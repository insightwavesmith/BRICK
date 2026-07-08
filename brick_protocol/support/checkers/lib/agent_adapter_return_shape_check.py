"""Agent adapter return-shape kernel-check leaf.

Pure relocation sibling of kernel_checks. Support checker mechanics only: it
observes Agent adapter return-shape, write-scope, read-tier, artifact-grounding,
and proof-obligation boundaries; it owns no axis crossing, decides no Movement,
and judges no success or quality.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from brick_protocol.support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    _ensure_import_identity,
)
from brick_protocol.support.checkers.lib.axis_vocab_drift_check import (
    _AXIS_VOCAB_RETIRED_WRITE_ADAPTER_REFS,
)


def _agent_instruction_packet_probe(repo: Path) -> Mapping[str, Any]:
    resources = importlib.import_module("brick_protocol.support.connection.agent_resources")
    packet = resources.render_agent_instruction_packet("dev", repo_root=repo)
    if not isinstance(packet, Mapping):
        raise ProfileError("agent instruction packet renderer did not return a mapping")
    required_keys = {
        "kind",
        "agent_object_ref",
        "role",
        "prompt_resources",
        "skill_resources",
        "hook_resources",
        "tool_policy_resources",
        "discipline_resources",
        "adapter_refs",
        "proof_limits",
        "not_proven",
    }
    missing = sorted(required_keys - set(packet))
    if missing:
        raise ProfileError(f"agent instruction packet missing required keys: {missing}")
    projection_keys = {"projection_target", "projection_status", "rendered_instruction_text"}
    leaked = sorted(projection_keys & set(packet))
    if leaked:
        raise ProfileError(f"agent instruction packet leaked projection-seed keys: {leaked}")
    if packet.get("kind") != "agent-instruction-packet":
        raise ProfileError("agent instruction packet kind drifted")
    if packet.get("agent_object_ref") != "agent-object:dev" or packet.get("role") != "dev":
        raise ProfileError("agent instruction packet did not preserve dev Agent Object identity")
    for key in (
        "prompt_resources",
        "skill_resources",
        "tool_policy_resources",
        "discipline_resources",
        "adapter_refs",
        "proof_limits",
        "not_proven",
    ):
        if not isinstance(packet.get(key), list) or not packet[key]:
            raise ProfileError(f"agent instruction packet {key} must be a non-empty list")
    hook_resources = packet.get("hook_resources")
    if not isinstance(hook_resources, Mapping) or "selected" not in hook_resources:
        raise ProfileError("agent instruction packet hook_resources must preserve selected hooks")
    # Manifest-shape pin (H4): skill_resources must be a fetch-on-demand MANIFEST
    # (ref + kind=skill-manifest + path), NOT eager inline bodies. A regression that
    # re-inlines the body (a 'body' key) is rejected, and the top-level
    # skill_manifest_refs stamp must mirror the rows so the DECLARED audit stays
    # honest (the OBSERVED fetch is not proven; only the offered set is recorded).
    skill_resources = packet.get("skill_resources")
    for row in skill_resources:  # non-empty list already asserted above
        if not isinstance(row, Mapping):
            raise ProfileError("agent instruction packet skill_resources row must be a mapping")
        if row.get("kind") != "skill-manifest":
            raise ProfileError(
                "agent instruction packet skill_resources row must be a skill-manifest "
                f"item (kind=skill-manifest), got kind={row.get('kind')!r}"
            )
        if not row.get("ref") or not row.get("path"):
            raise ProfileError("agent instruction packet skill-manifest row must carry ref + path")
        if "body" in row:
            raise ProfileError(
                "agent instruction packet skill_resources regressed to an EAGER body "
                "(a manifest row must not inline the SKILL.md body)"
            )
    manifest_refs = packet.get("skill_manifest_refs")
    if not isinstance(manifest_refs, list) or len(manifest_refs) != len(skill_resources):
        raise ProfileError(
            "agent instruction packet skill_manifest_refs stamp must mirror skill_resources "
            f"(got {manifest_refs!r})"
        )
    return packet


def _agent_instruction_packet_for_role(repo: Path, role: str) -> Mapping[str, Any]:
    resources = importlib.import_module("brick_protocol.support.connection.agent_resources")
    packet = resources.render_agent_instruction_packet(role, repo_root=repo)
    expected_ref = f"agent-object:{role}"
    if not isinstance(packet, Mapping):
        raise ProfileError(f"{role} instruction packet renderer did not return a mapping")
    if packet.get("kind") != "agent-instruction-packet":
        raise ProfileError(f"{role} instruction packet kind drifted")
    if packet.get("agent_object_ref") != expected_ref or packet.get("role") != role:
        raise ProfileError(f"{role} instruction packet did not preserve Agent Object identity")
    return packet


def _agent_adapter_request_instruction_packet_probe(
    adapter: Any,
    instruction_packet: Mapping[str, Any],
    required_shape: str,
) -> object:
    adapter_constants = importlib.import_module("brick_protocol.support.connection.adapter_constants")
    request_fields = {field.name for field in fields(adapter.AgentAdapterRequest)}
    if "agent_instruction_packet" not in request_fields:
        raise ProfileError("AgentAdapterRequest must admit agent_instruction_packet")
    request = adapter.AgentAdapterRequest(
        building_id="agent-adapter-return-shape-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        required_return_shape=required_shape,
        agent_instruction_packet=instruction_packet,
    )
    observed = getattr(request, "agent_instruction_packet")
    if not isinstance(observed, Mapping):
        raise ProfileError("AgentAdapterRequest did not preserve agent_instruction_packet")
    for key in ("kind", "agent_object_ref", "role"):
        if observed.get(key) != instruction_packet.get(key):
            raise ProfileError(f"AgentAdapterRequest agent_instruction_packet lost {key}")
    return request


def _agent_effective_write_probe(
    repo: Path,
    adapter: Any,
    instruction_packet: Mapping[str, Any],
) -> int:
    adapter_constants = importlib.import_module("brick_protocol.support.connection.adapter_constants")
    adapter_grant_policy = importlib.import_module("brick_protocol.support.connection.adapter_grant_policy")
    adapter_local_cli = importlib.import_module("brick_protocol.support.connection.adapter_local_cli")
    write_scope = {
        "allowed_paths": ["brick_protocol/support/connection/agent_adapter.py"],
        "forbidden_paths": [".git/**", ".env"],
        "commit_allowed": False,
        "push_allowed": False,
    }
    write_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    if not adapter.agent_request_effective_write(write_request):
        raise ProfileError("codex-local write_scope request did not become effective_write")
    if adapter_local_cli._codex_sandbox_for_request(write_request) != "workspace-write":
        raise ProfileError("effective_write request did not select workspace-write sandbox")
    write_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            write_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    if "You may edit files only inside the Brick-declared write_scope.allowed_paths." not in write_prompt.get(
        "rules",
        [],
    ):
        raise ProfileError("effective_write prompt did not expose scoped write rules")
    if write_prompt.get("agent_instruction_packet", {}).get("kind") != "agent-instruction-packet":
        raise ProfileError("effective_write prompt did not carry Agent instruction packet")

    non_dev_packet = dict(instruction_packet)
    non_dev_packet["agent_object_ref"] = "agent-object:cto-lead"
    non_dev_packet["role"] = "cto-lead"
    non_dev_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-non-dev-probe",
        agent_object_ref="agent-object:cto-lead",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
        write_scope=write_scope,
        agent_instruction_packet=non_dev_packet,
    )
    if not adapter.agent_request_effective_write(non_dev_request):
        raise ProfileError("effective_write was incorrectly tied to agent-object:dev")

    try:
        adapter.connect_agent_brain(
            non_dev_request,
            command_runner=lambda _args, _cwd, _timeout: (_ for _ in ()).throw(
                AssertionError("effective write reached command runner without observation")
            ),
            cwd=repo,
        )
    except ValueError as exc:
        if "effective write requires write observation before adapter execution" not in str(exc):
            raise ProfileError("effective_write without observation rejected with wrong reason") from exc
    else:
        raise ProfileError("effective_write reached adapter execution without observation marker")

    adapter._mark_effective_write_observation_path(non_dev_request, repo)
    try:
        adapter.connect_agent_brain(
            non_dev_request,
            command_runner=lambda _args, _cwd, _timeout: (_ for _ in ()).throw(
                AssertionError("effective write reached command runner after cwd mismatch")
            ),
            cwd=repo / "brick_protocol" / "support",
        )
    except ValueError as exc:
        if "effective write observation cwd must match adapter execution cwd" not in str(exc):
            raise ProfileError("effective_write cwd mismatch rejected with wrong reason") from exc
    else:
        raise ProfileError("effective_write observation marker accepted mismatched cwd")

    # REDO (Smith 0623 struct-surgery): the adapter EXPOSES raw effective-write
    # request inputs and SUPPORT/RECORDING derives the named write-policy facts. The
    # request observer derives nothing and stops nothing.
    from brick_protocol.support.recording.agent_step_observation import (
        derive_effective_write_request_facts as _derive_write_policy_facts,
    )

    def _recorded_write_policy_facts(request: Any) -> tuple[str, ...]:
        return _derive_write_policy_facts(
            **adapter.agent_request_effective_write_raw_inputs(request)
        )

    # A write_scope WITHOUT the read-write tool policy no longer STOPS request
    # construction -- the dev Agent omitting tool-policy:read-write-scoped is RECORDED
    # (by brick_protocol/support/recording) as missing_agent_write_policy, and the building continues.
    # Brick recommends, the Agent is free, the worktree isolates, merge-review is the
    # real gate. The probe asserts the request CONSTRUCTS (no raise) AND the recorded
    # fact carries the token.
    no_policy_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-negative-no-policy",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    no_policy_facts = _recorded_write_policy_facts(no_policy_request)
    if not any("missing_agent_write_policy" in fact for fact in no_policy_facts):
        raise ProfileError(
            "write_scope without read-write tool policy must be RECORDED as "
            f"missing_agent_write_policy (move+record only), observed {no_policy_facts!r}"
        )

    # A selected adapter whose mapping does not support observed workspace write
    # no longer STOPS construction
    # -- the disposition is RECORDED (by brick_protocol/support/recording) as
    # missing_adapter_write_capability and the building continues. The probe asserts
    # the request CONSTRUCTS (no raise), never becomes effective_write, and the
    # recorded fact carries the token.
    unsupported_adapter_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-negative-unsupported-adapter",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    if adapter.agent_request_effective_write(unsupported_adapter_request):
        raise ProfileError("read-only adapter write_scope request became effective_write")
    unsupported_adapter_facts = _recorded_write_policy_facts(unsupported_adapter_request)
    if not any(
        "missing_adapter_write_capability" in fact for fact in unsupported_adapter_facts
    ):
        raise ProfileError(
            "unsupported observed-write adapter with write_scope must be RECORDED as "
            f"missing_adapter_write_capability (move+record only), observed "
            f"{unsupported_adapter_facts!r}"
        )

    # P1 Adapter Authority Repair: gemini-local is a CLI adapter that may project
    # write_file / replace / run_shell_command ONLY through the same effective_write
    # intersection as codex/claude: Brick write_scope NEED + read-write-scoped Agent
    # policy + observed-write adapter mapping. These probes assert the positive and
    # the no-policy negative at the grant/projection layer before any live CLI call.
    gemini_write_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-gemini-local-positive",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    if not adapter.agent_request_effective_write(gemini_write_request):
        raise ProfileError("gemini-local write_scope request did not become effective_write")
    gemini_allow, gemini_deny = adapter_grant_policy._gemini_admin_policy_partition_for_request(
        gemini_write_request
    )
    for required_tool in ("write_file", "replace", "run_shell_command"):
        if required_tool not in gemini_allow:
            raise ProfileError(
                "gemini-local effective_write did not allow write/shell tool "
                f"{required_tool!r}; allow={gemini_allow!r}"
            )
        if required_tool in gemini_deny:
            raise ProfileError(
                "gemini-local effective_write still denied write/shell tool "
                f"{required_tool!r}; deny={gemini_deny!r}"
            )
    gemini_write_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            gemini_write_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_GEMINI_LOCAL],
        )
    )
    gemini_write_rules = list(gemini_write_prompt.get("rules", []))
    if any("write and shell tools remain blocked" in rule for rule in gemini_write_rules):
        raise ProfileError("gemini-local effective_write prompt still says write/shell are blocked")
    if not any("write_file, replace, and run_shell_command" in rule for rule in gemini_write_rules):
        raise ProfileError("gemini-local effective_write prompt did not name scoped write/shell tools")

    inspector_packet = _agent_instruction_packet_for_role(repo, "inspector")
    gemini_probe_write_scope = {
        "allowed_paths": ["brick_protocol/support/checkers/generated-probes/**"],
        "forbidden_paths": [".git/**", "brick_protocol/agent/**", "brick_protocol/brick/**", "brick_protocol/link/**"],
        "commit_allowed": False,
        "push_allowed": False,
    }
    gemini_inspector_probe_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-gemini-local-inspector-probe",
        agent_object_ref="agent-object:inspector",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        hook_refs=("hook:reviewer-no-mutation",),
        write_scope=gemini_probe_write_scope,
        agent_instruction_packet=inspector_packet,
    )
    if not adapter.agent_request_effective_write(gemini_inspector_probe_request):
        raise ProfileError(
            "gemini-local inspector probe write_scope request did not become effective_write"
        )
    gemini_probe_allow, gemini_probe_deny = (
        adapter_grant_policy._gemini_admin_policy_partition_for_request(
            gemini_inspector_probe_request
        )
    )
    for required_tool in ("write_file", "replace", "run_shell_command"):
        if required_tool not in gemini_probe_allow:
            raise ProfileError(
                "gemini-local inspector effective probe_write did not allow write/shell tool "
                f"{required_tool!r}; allow={gemini_probe_allow!r}"
            )
        if required_tool in gemini_probe_deny:
            raise ProfileError(
                "gemini-local inspector effective probe_write still denied write/shell tool "
                f"{required_tool!r}; deny={gemini_probe_deny!r}"
            )
    gemini_probe_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            gemini_inspector_probe_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_GEMINI_LOCAL],
        )
    )
    gemini_probe_rules = list(gemini_probe_prompt.get("rules", []))
    if not gemini_probe_prompt.get("native_grant", {}).get("write_effective"):
        raise ProfileError("gemini-local inspector probe prompt did not carry write_effective")
    if any("write and shell tools remain blocked" in rule for rule in gemini_probe_rules):
        raise ProfileError(
            "gemini-local inspector effective probe_write prompt still says write/shell are blocked"
        )
    if not any("effective probe_write / verification_write" in rule for rule in gemini_probe_rules):
        raise ProfileError(
            "gemini-local inspector effective probe_write prompt did not name probe/verification write"
        )

    captured_gemini_write: dict[str, Any] = {}

    def _capture_gemini_write_runner(
        args: Sequence[str],
        cwd: Path,
        timeout: int,
        *,
        env: Mapping[str, str] | None = None,
    ) -> Any:
        del timeout
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return adapter.LocalCliCompleted(call, 0, "0.46.0", "")
        captured_gemini_write["args"] = call
        captured_gemini_write["cwd"] = cwd
        captured_gemini_write["env_has_api_key"] = bool(
            (env or {}).get("GEMINI_API_KEY") or (env or {}).get("GOOGLE_API_KEY")
        )
        if "--admin-policy" in call:
            policy_path = Path(call[call.index("--admin-policy") + 1])
            captured_gemini_write["policy_text"] = policy_path.read_text(encoding="utf-8")
        return adapter.LocalCliCompleted(
            call,
            0,
            json.dumps(
                {
                    "response": "{}",
                    "stats": {
                        "tools": {
                            "totalCalls": 3,
                            "byName": {
                                "write_file": 1,
                                "replace": 1,
                                "run_shell_command": 1,
                            },
                        }
                    },
                }
            ),
            "",
        )

    saved_env = {name: os.environ.get(name) for name in adapter._GEMINI_API_KEY_ENV_VARS}
    for name in adapter._GEMINI_API_KEY_ENV_VARS:
        os.environ.pop(name, None)
    os.environ["GEMINI_API_KEY"] = "probe-key"
    adapter._mark_effective_write_observation_path(gemini_write_request, repo)
    try:
        gemini_write_result = adapter.connect_agent_brain(
            gemini_write_request,
            command_runner=_capture_gemini_write_runner,
            cwd=repo,
            timeout_seconds=5,
        )
    finally:
        for name in adapter._GEMINI_API_KEY_ENV_VARS:
            os.environ.pop(name, None)
            if saved_env[name] is not None:
                os.environ[name] = saved_env[name]
    if captured_gemini_write.get("cwd") != repo:
        raise ProfileError("gemini-local effective_write did not run from adapter cwd")
    if not captured_gemini_write.get("env_has_api_key"):
        raise ProfileError("gemini-local effective_write did not carry API-key env")
    policy_text = str(captured_gemini_write.get("policy_text", ""))
    for required_tool in ("write_file", "replace", "run_shell_command"):
        if required_tool not in policy_text:
            raise ProfileError(
                "gemini-local effective_write admin policy omitted write/shell tool "
                f"{required_tool!r}"
            )
    observed = tuple(
        gemini_write_result.adapter_raw_observations.get(
            "non_granted_gemini_tool_names",
            (),
        )
    )
    for required_tool in ("write_file", "replace", "run_shell_command"):
        if required_tool in observed:
            raise ProfileError(
                "gemini-local effective_write recorded a granted write/shell tool as "
                f"non-granted: {observed!r}"
            )

    gemini_no_policy_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-gemini-local-no-policy",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(),
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    if adapter.agent_request_effective_write(gemini_no_policy_request):
        raise ProfileError("gemini-local write_scope without read-write policy became effective_write")
    no_policy_allow, no_policy_deny = adapter_grant_policy._gemini_admin_policy_partition_for_request(
        gemini_no_policy_request
    )
    for forbidden_tool in ("write_file", "replace", "run_shell_command"):
        if forbidden_tool in no_policy_allow or forbidden_tool not in no_policy_deny:
            raise ProfileError(
                "gemini-local no-policy request did not deny write/shell tool "
                f"{forbidden_tool!r}; allow={no_policy_allow!r} deny={no_policy_deny!r}"
            )

    for retired_adapter_ref in _AXIS_VOCAB_RETIRED_WRITE_ADAPTER_REFS:
        try:
            adapter.AgentAdapterRequest(
                building_id="agent-effective-write-negative-retired-adapter",
                agent_object_ref="agent-object:dev",
                adapter_ref=retired_adapter_ref,
                brick_instance_ref="brick-work",
                next_brick_instance_ref="brick-closure",
                tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
                write_scope=write_scope,
                agent_instruction_packet=instruction_packet,
            )
        except ValueError as exc:
            message = str(exc)
            if "retired" not in message and "not admitted" not in message:
                raise ProfileError(
                    f"retired write adapter {retired_adapter_ref} rejected with wrong reason"
                ) from exc
        else:
            raise ProfileError(f"retired write adapter {retired_adapter_ref} was not rejected")

    bad_packet = dict(instruction_packet)
    bad_packet["agent_object_ref"] = "agent-object:qa"
    try:
        adapter.AgentAdapterRequest(
            building_id="agent-instruction-packet-negative-mismatch",
            agent_object_ref="agent-object:dev",
            adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
            brick_instance_ref="brick-work",
            next_brick_instance_ref="brick-closure",
            agent_instruction_packet=bad_packet,
        )
    except ValueError as exc:
        if "agent_instruction_packet.agent_object_ref must match" not in str(exc):
            raise ProfileError("instruction packet mismatch rejected with wrong reason") from exc
    else:
        raise ProfileError("mismatched instruction packet was not rejected")

    # claude-local is now write-capable (same observed-write 3-gate as codex).
    # A claude write request must select scoped write CLI knobs; an ambiguous
    # no-tool-policy claude read request must fail closed to the no-tool plan
    # shape. The separate read-tier probe covers read-only browse through the
    # declared tool list. Live in-scope/out-of-scope claude writes remain
    # NOT-PROVEN (no OS sandbox); these assert the knobs only.
    claude_write_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-claude-positive",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
        write_scope=write_scope,
        agent_instruction_packet=instruction_packet,
    )
    if not adapter.agent_request_effective_write(claude_write_request):
        raise ProfileError("claude-local write_scope request did not become effective_write")
    knobs = adapter_local_cli._claude_cli_invocation(claude_write_request)
    if knobs["permission_mode"] != "acceptEdits":
        raise ProfileError("claude effective_write did not select acceptEdits")
    write_tools = (
        [t.strip() for t in knobs["tools"].split(",") if t.strip()]
        if knobs["tools"]
        else []
    )
    if set(write_tools) != {"Read", "Grep", "Glob", "Edit", "Write", "Bash"}:
        raise ProfileError(
            "claude effective_write did not expose the exact comma-separated scoped "
            f"write tool set; observed {knobs['tools']!r}"
        )
    if knobs.get("allowed_tools") != knobs["tools"]:
        raise ProfileError(
            "claude effective_write did not project the scoped tool set into "
            f"allowed_tools; observed {knobs.get('allowed_tools')!r}"
        )
    if knobs["system_prompt"] != adapter._CLAUDE_SCOPED_WRITE_SYSTEM_PROMPT:
        raise ProfileError("claude effective_write did not use the scoped-write system prompt")
    captured_claude_write_args: dict[str, tuple[str, ...]] = {}

    def _capture_claude_write_runner(
        args: Sequence[str],
        cwd: Path,
        timeout: int,
        *,
        env: Mapping[str, str] | None = None,
    ) -> Any:
        del cwd, timeout, env
        captured_claude_write_args["args"] = tuple(str(arg) for arg in args)
        return adapter.LocalCliCompleted(
            args=captured_claude_write_args["args"],
            return_code=0,
            stdout='{"result":"{}"}',
            stderr="",
        )

    adapter_local_cli._invoke_local_cli(
        adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CLAUDE_LOCAL],
        claude_write_request,
        "{}",
        cwd=repo,
        timeout_seconds=9,
        command_runner=_capture_claude_write_runner,
    )
    claude_write_args = captured_claude_write_args.get("args", ())
    if "--tools" not in claude_write_args:
        raise ProfileError("claude effective_write argv omitted --tools")
    if "--allowedTools" not in claude_write_args:
        raise ProfileError(
            "claude effective_write argv omitted --allowedTools; Bash/checker "
            "commands would remain provider-approval gated"
        )
    tools_arg = claude_write_args[claude_write_args.index("--tools") + 1]
    allowed_tools_arg = claude_write_args[claude_write_args.index("--allowedTools") + 1]
    if allowed_tools_arg != tools_arg:
        raise ProfileError(
            "claude effective_write argv allowedTools drifted from tools: "
            f"{allowed_tools_arg!r} != {tools_arg!r}"
        )
    if "Bash" not in {tool.strip() for tool in allowed_tools_arg.split(",") if tool.strip()}:
        raise ProfileError("claude effective_write argv did not pre-allow Bash")

    claude_read_request = adapter.AgentAdapterRequest(
        building_id="agent-effective-write-claude-read",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-work",
        next_brick_instance_ref="brick-closure",
        agent_instruction_packet=instruction_packet,
    )
    if adapter.agent_request_effective_write(claude_read_request):
        raise ProfileError("claude read request became effective_write")
    knobs_read = adapter_local_cli._claude_cli_invocation(claude_read_request)
    if knobs_read["permission_mode"] != "plan":
        raise ProfileError("claude read request did not stay in plan mode")
    if knobs_read["tools"] != "":
        raise ProfileError("claude read request exposed tools")
    if knobs_read["system_prompt"] != adapter._CLAUDE_NONINTERACTIVE_SYSTEM_PROMPT:
        raise ProfileError("claude read request did not use the read-only system prompt")

    return 15


def _agent_read_tier_probe(repo: Path, adapter: Any) -> int:
    adapter_constants = importlib.import_module("brick_protocol.support.connection.adapter_constants")
    adapter_grant_policy = importlib.import_module("brick_protocol.support.connection.adapter_grant_policy")
    adapter_local_cli = importlib.import_module("brick_protocol.support.connection.adapter_local_cli")
    resources = importlib.import_module("brick_protocol.support.connection.agent_resources")
    qa_packet = _agent_instruction_packet_for_role(repo, "qa")
    pm_packet = _agent_instruction_packet_for_role(repo, "pm-lead")
    cto_packet = _agent_instruction_packet_for_role(repo, "cto-lead")
    dev_packet = _agent_instruction_packet_for_role(repo, "dev")
    inspector_packet = _agent_instruction_packet_for_role(repo, "inspector")
    expected_known_policies = {
        adapter_constants.LEADER_COORDINATION_TOOL_POLICY_REF,
        adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,
        adapter_constants.READ_WRITE_TOOL_POLICY_REF,
        adapter_constants.REVIEWER_READONLY_TOOL_POLICY_REF,
        adapter_constants.WEB_CAPABLE_TOOL_POLICY_REF,
    }
    if set(adapter_constants.KNOWN_TOOL_POLICY_REFS) != expected_known_policies:
        raise ProfileError(
            "read-tier known tool-policy vocabulary drifted; observed "
            f"{sorted(adapter_constants.KNOWN_TOOL_POLICY_REFS)!r}"
        )
    tool_policy_dir = repo / "brick_protocol" / "agent" / "tool_policies"
    discovered_policy_refs: set[str] = set()
    for path in sorted(tool_policy_dir.glob("*.yaml")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise ProfileError(f"{path.relative_to(repo).as_posix()} must load as a JSON object")
        ref = data.get("tool_policy_ref")
        if not isinstance(ref, str):
            raise ProfileError(f"{path.relative_to(repo).as_posix()} missing tool_policy_ref")
        discovered_policy_refs.add(ref)
        resources.resolve_native_grant(
            [
                {
                    "ref": ref,
                    "kind": "tool_policy",
                    "path": path.relative_to(repo).as_posix(),
                    "data": data,
                }
            ],
            tool_policy_refs=[ref],
            write_need=(ref in adapter_constants.WRITE_TIER_TOOL_POLICY_REFS),
        )
    if not expected_known_policies.issubset(discovered_policy_refs):
        raise ProfileError(
            "native_grant discovery missed known tool-policy refs: "
            f"{sorted(expected_known_policies - discovered_policy_refs)!r}"
        )
    web_roles: list[str] = []
    for object_ref in resources.list_agent_object_refs(repo):
        role = object_ref.removeprefix("agent-object:")
        packet = _agent_instruction_packet_for_role(repo, role)
        tool_policy_refs = {
            resource["ref"]
            for resource in packet.get("tool_policy_resources", [])
            if isinstance(resource, Mapping) and isinstance(resource.get("ref"), str)
        }
        if adapter_constants.WEB_CAPABLE_TOOL_POLICY_REF in tool_policy_refs:
            web_roles.append(role)
        for resource in packet.get("tool_policy_resources", []):
            data = resource.get("data") if isinstance(resource, Mapping) else None
            grant = data.get("native_grant") if isinstance(data, Mapping) else None
            if not isinstance(grant, Mapping):
                raise ProfileError(f"{role} tool policy resource missing native_grant")
            if any(key in grant for key in ("model", "credential_body", "provider_session_id")):
                raise ProfileError(f"{role} native_grant leaked forbidden axis/provider key")
    if sorted(web_roles) != ["design-lead", "pm-lead"]:
        raise ProfileError(
            "tool-policy:web-capable must be attached only to pm-lead/design-lead, "
            f"observed {sorted(web_roles)!r}"
        )
    for role in ("qa", "inspector", "qa-lead"):
        packet = _agent_instruction_packet_for_role(repo, role)
        semantic_capability = packet.get("semantic_capability")
        if not isinstance(semantic_capability, Mapping):
            raise ProfileError(f"{role} instruction packet missing semantic_capability")
        declared_classes = semantic_capability.get("declared_policy_semantic_capability_classes")
        max_classes = semantic_capability.get("max_semantic_capability_classes")
        if "source_write" in (declared_classes or ()) or "artifact_write" in (
            declared_classes or ()
        ):
            raise ProfileError(
                f"{role} reviewer-intent policy structurally admits source/artifact write: "
                f"{declared_classes!r}"
            )
        if "source_write" in (max_classes or ()) or "artifact_write" in (max_classes or ()):
            raise ProfileError(
                f"{role} reviewer-intent effective semantic capability leaked source/artifact write: "
                f"{max_classes!r}"
            )
    dev_resolution = resources.resolve_native_grant(
        dev_packet["tool_policy_resources"],
        tool_policy_refs=[
            resource["ref"]
            for resource in dev_packet["tool_policy_resources"]
            if isinstance(resource, Mapping)
        ],
        write_need=False,
    )
    if dev_resolution.get("capabilities") != ["read"]:
        raise ProfileError(
            "read-write-scoped without Brick write NEED must resolve native capabilities to read only"
        )
    dev_write_resolution = resources.resolve_native_grant(
        dev_packet["tool_policy_resources"],
        tool_policy_refs=[
            resource["ref"]
            for resource in dev_packet["tool_policy_resources"]
            if isinstance(resource, Mapping)
        ],
        write_need=True,
    )
    if dev_write_resolution.get("capabilities") != ["read", "write"]:
        raise ProfileError(
            "read-write-scoped with Brick write NEED must resolve native capabilities to read/write"
        )

    reviewer_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-reviewer-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.REVIEWER_READONLY_TOOL_POLICY_REF,),
        required_return_shape="observed_evidence, evidence_used, not_proven",
        agent_instruction_packet=qa_packet,
    )
    if not adapter.agent_request_read_tier(reviewer_request):
        raise ProfileError("reviewer-readonly non-write codex request did not enter read tier")
    reviewer_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            reviewer_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    reviewer_rules = list(reviewer_prompt.get("rules", []))
    if "Do not use tools or hooks." in reviewer_rules:
        raise ProfileError("read-tier codex reviewer prompt still rendered the none-tier no-tools rule")
    expected_read_rule = (
        "You may use read-only repository inspection tools only: read files, inspect diffs, "
        "search with grep/glob, and run checker commands."
    )
    if expected_read_rule not in reviewer_rules:
        raise ProfileError("read-tier codex reviewer prompt did not expose repository inspection rule")
    forbidden_write_permission_phrases = (
        "You may edit files only inside",
        "write_scope.allowed_paths",
        "Read, Grep, Glob, Edit, Write, Bash",
        "Bash",
    )
    for phrase in forbidden_write_permission_phrases:
        if any(phrase in rule for rule in reviewer_rules):
            raise ProfileError(
                "read-tier codex reviewer prompt leaked write-tier permission phrase "
                f"{phrase!r}"
            )

    unknown_policy_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-unknown-policy-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.REVIEWER_READONLY_TOOL_POLICY_REF, "tool-policy:unknown"),
        required_return_shape="observed_evidence, evidence_used, not_proven",
        agent_instruction_packet=qa_packet,
    )
    if adapter.agent_request_read_tier(unknown_policy_request):
        raise ProfileError("reviewer-readonly plus unknown tool policy entered read tier")
    unknown_policy_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            unknown_policy_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    if "Do not use tools or hooks." not in unknown_policy_prompt.get("rules", []):
        raise ProfileError("unknown tool policy request did not fail closed to none tier")
    if expected_read_rule in unknown_policy_prompt.get("rules", []):
        raise ProfileError("unknown tool policy request still rendered read-tier inspection rule")

    leader_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-leader-probe",
        agent_object_ref="agent-object:cto-lead",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-design",
        next_brick_instance_ref="brick-work",
        tool_policy_refs=(
            adapter_constants.LEADER_COORDINATION_TOOL_POLICY_REF,
            adapter_constants.READ_WRITE_TOOL_POLICY_REF,
        ),
        required_return_shape="observed_evidence, evidence_refs, not_proven",
        agent_instruction_packet=cto_packet,
    )
    if not adapter.agent_request_read_tier(leader_request):
        raise ProfileError("leader-coordination non-write claude request did not enter read tier")
    leader_knobs = adapter_local_cli._claude_cli_invocation(leader_request)
    if leader_knobs["permission_mode"] != "acceptEdits":
        raise ProfileError("read-tier claude request must use acceptEdits with the declared read-only tool list")
    leader_tools = [tool.strip() for tool in leader_knobs["tools"].split(",") if tool.strip()]
    if leader_tools != ["Read", "Grep", "Glob"]:
        raise ProfileError(f"read-tier claude tools must be Read/Grep/Glob only, got {leader_tools}")
    if "Edit" in leader_tools or "Write" in leader_tools or "Bash" in leader_tools:
        raise ProfileError("read-tier claude request leaked Edit/Write/Bash tools")
    if leader_knobs["system_prompt"] != adapter._CLAUDE_READ_ONLY_SYSTEM_PROMPT:
        raise ProfileError("read-tier claude request did not use the read-only system prompt")

    # CLEAN-READTIER-0617 / CLAUDE-READ-FULL-ADAPTER-0624: read/write tier is no
    # longer a support-side authority over the tool-policy label. A read-only Brick
    # (no observed write) paired with a tool-capable Agent browses read-only through
    # declared read tools. Claude uses the normal acceptEdits invocation plane with
    # only Read/Grep/Glob; provider plan mode is not the read boundary. (Write still
    # requires write_scope, which routes through agent_request_effective_write.)
    dev_nonwrite_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-dev-readonly-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-readonly-worker",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        agent_instruction_packet=dev_packet,
    )
    if adapter.agent_request_effective_write(dev_nonwrite_request):
        raise ProfileError("read-write-scoped without write_scope must not be effective_write")
    if not adapter.agent_request_read_tier(dev_nonwrite_request):
        raise ProfileError(
            "read-only Brick + tool-capable codex Agent (read-write-scoped, no write_scope) "
            "did not enter the read tier under the uniform CLEAN-READTIER rule"
        )
    dev_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            dev_nonwrite_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    dev_rules = list(dev_prompt.get("rules", []))
    if "Do not use tools or hooks." in dev_rules:
        raise ProfileError("read-tier read-write-scoped codex prompt still rendered the none-tier no-tools rule")
    if expected_read_rule not in dev_rules:
        raise ProfileError("read-tier read-write-scoped codex prompt did not expose repository inspection rule")
    # Read tier must not leak write-tier permission: no edit-allowed phrasing.
    for phrase in ("You may edit files only inside", "write_scope.allowed_paths"):
        if any(phrase in rule for rule in dev_rules):
            raise ProfileError(
                f"read-tier read-write-scoped codex prompt leaked write-tier permission phrase {phrase!r}"
            )

    reviewer_no_mutation_write_scope = {
        "allowed_paths": ["."],
        "forbidden_paths": [".git/**"],
    }
    reviewer_no_mutation_request = adapter.AgentAdapterRequest(
        building_id="agent-reviewer-no-mutation-write-scope-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-code-attack-qa",
        next_brick_instance_ref="brick-closure",
        hook_refs=("hook:reviewer-no-mutation",),
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        required_return_shape="observed_evidence, evidence_used, not_proven",
        agent_instruction_packet=qa_packet,
        write_scope=reviewer_no_mutation_write_scope,
    )
    if not adapter.agent_request_effective_write(reviewer_no_mutation_request):
        raise ProfileError("reviewer-no-mutation probe stopped recording effective_write input")
    reviewer_no_mutation_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            reviewer_no_mutation_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    reviewer_no_mutation_rules = list(reviewer_no_mutation_prompt.get("rules", []))
    required_taxonomy_rules = (
        "hook:reviewer-no-mutation blocks source_write",
        "probe_write / verification_write",
        "disposable work-area",
        "full filesystem-enforced source/probe split is not proven",
    )
    for required in required_taxonomy_rules:
        if not any(required in rule for rule in reviewer_no_mutation_rules):
            raise ProfileError(
                "reviewer-no-mutation prompt did not carry capability-taxonomy rule "
                f"{required!r}"
            )
    if not any("Do not create, edit, delete, or rewrite source files as source truth" in rule for rule in reviewer_no_mutation_rules):
        raise ProfileError("reviewer-no-mutation prompt did not carry the source_write ban")
    if adapter_local_cli._codex_sandbox_for_request(reviewer_no_mutation_request) != "workspace-write":
        raise ProfileError(
            "reviewer-no-mutation codex projection did not preserve declared work-area write sandbox"
        )
    claude_reviewer_no_mutation_request = adapter.AgentAdapterRequest(
        building_id="agent-reviewer-no-mutation-claude-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-code-attack-qa",
        next_brick_instance_ref="brick-closure",
        hook_refs=("hook:reviewer-no-mutation",),
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        agent_instruction_packet=qa_packet,
        write_scope=reviewer_no_mutation_write_scope,
    )
    claude_reviewer_knobs = adapter_local_cli._claude_cli_invocation(claude_reviewer_no_mutation_request)
    claude_reviewer_tools = [
        tool.strip()
        for tool in claude_reviewer_knobs["tools"].split(",")
        if tool.strip()
    ]
    for tool_name in ("Read", "Grep", "Glob", "Edit", "Write", "Bash"):
        if tool_name not in claude_reviewer_tools:
            raise ProfileError(
                "reviewer-no-mutation claude projection did not preserve work-area "
                f"tool {tool_name!r}: {claude_reviewer_tools!r}"
            )
    if claude_reviewer_knobs["system_prompt"] != adapter._CLAUDE_SCOPED_WRITE_SYSTEM_PROMPT:
        raise ProfileError(
            "reviewer-no-mutation claude projection did not use scoped-write system prompt"
        )
    gemini_reviewer_no_mutation_request = adapter.AgentAdapterRequest(
        building_id="agent-reviewer-no-mutation-gemini-probe",
        agent_object_ref="agent-object:inspector",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-axis-attack-qa",
        next_brick_instance_ref="brick-closure",
        hook_refs=("hook:reviewer-no-mutation",),
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        agent_instruction_packet=inspector_packet,
        write_scope=reviewer_no_mutation_write_scope,
    )
    gemini_reviewer_allow, gemini_reviewer_deny = adapter_grant_policy._gemini_admin_policy_partition_for_request(
        gemini_reviewer_no_mutation_request
    )
    for tool_name in ("write_file", "replace", "run_shell_command"):
        if tool_name not in gemini_reviewer_allow or tool_name in gemini_reviewer_deny:
            raise ProfileError(
                "reviewer-no-mutation gemini projection did not preserve work-area probe tool "
                f"{tool_name!r}"
            )
    if "read_file" not in gemini_reviewer_allow:
        raise ProfileError("reviewer-no-mutation gemini projection did not preserve read tools")

    fugu_nonwrite_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-fugu-readonly-probe",
        agent_object_ref="agent-object:dev",
        adapter_ref=adapter_constants.ADAPTER_CODEX_FUGU_LOCAL,
        brick_instance_ref="brick-readonly-worker",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.READ_WRITE_TOOL_POLICY_REF,),
        agent_instruction_packet=dev_packet,
    )
    if adapter.agent_request_effective_write(fugu_nonwrite_request):
        raise ProfileError("fugu read-write-scoped without write_scope must not be effective_write")
    if not adapter.agent_request_read_tier(fugu_nonwrite_request):
        raise ProfileError(
            "read-only Brick + tool-capable fugu Agent (read-write-scoped, no write_scope) "
            "did not enter the read tier"
        )
    fugu_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            fugu_nonwrite_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_FUGU_LOCAL],
        )
    )
    fugu_rules = list(fugu_prompt.get("rules", []))
    if "Do not use tools or hooks." in fugu_rules:
        raise ProfileError("read-tier read-write-scoped fugu prompt still rendered the none-tier no-tools rule")
    if expected_read_rule not in fugu_rules:
        raise ProfileError("read-tier read-write-scoped fugu prompt did not expose repository inspection rule")
    for phrase in ("You may edit files only inside", "write_scope.allowed_paths"):
        if any(phrase in rule for rule in fugu_rules):
            raise ProfileError(
                f"read-tier read-write-scoped fugu prompt leaked write-tier permission phrase {phrase!r}"
            )

    gemini_inspect_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-gemini-inspect-probe",
        agent_object_ref="agent-object:inspector",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-inspect",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        agent_instruction_packet=inspector_packet,
    )
    if not adapter.agent_request_read_tier(gemini_inspect_request):
        raise ProfileError("gemini-local read-write-scoped request did not enter read tier")
    gemini_inspect_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            gemini_inspect_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_GEMINI_LOCAL],
        )
    )
    gemini_inspect_rules = list(gemini_inspect_prompt.get("rules", []))
    if "Do not use tools or hooks." in gemini_inspect_rules:
        raise ProfileError("gemini-local read-write-scoped prompt still rendered no-tools rule")
    if expected_read_rule not in gemini_inspect_rules:
        raise ProfileError("gemini-local read-write-scoped prompt did not expose repository inspection rule")
    if not any(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF in rule for rule in gemini_inspect_rules):
        raise ProfileError("gemini-local probe-write-scoped prompt omitted its admitted policy ref")
    if not any("Gemini local native grant may use only read_file" in rule for rule in gemini_inspect_rules):
        raise ProfileError("gemini-local read-write-scoped prompt did not pin read-only tool allow-list")

    gemini_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-gemini-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.REVIEWER_READONLY_TOOL_POLICY_REF,),
        agent_instruction_packet=qa_packet,
    )
    if adapter_constants.ADAPTER_GEMINI_LOCAL not in set(qa_packet.get("adapter_refs", ())):
        raise ProfileError("qa instruction packet did not admit adapter:gemini-local")
    if adapter.agent_request_effective_write(gemini_request):
        raise ProfileError("gemini-local reviewer-readonly request opened effective write")
    if not adapter.agent_request_read_tier(gemini_request):
        raise ProfileError("gemini-local reviewer-readonly request did not enter read tier")
    gemini_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            gemini_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_GEMINI_LOCAL],
        )
    )
    gemini_rules = list(gemini_prompt.get("rules", []))
    if "Do not use tools or hooks." in gemini_rules:
        raise ProfileError("read-tier gemini-local prompt still rendered the none-tier no-tools rule")
    if expected_read_rule not in gemini_rules:
        raise ProfileError("read-tier gemini-local prompt did not expose repository inspection rule")
    if any("adapter:gemini-local remains in the none tier" in rule for rule in gemini_rules):
        raise ProfileError("read-tier gemini-local prompt still documented the retired none-tier limit")
    if not any("Gemini local native grant may use only read_file" in rule for rule in gemini_rules):
        raise ProfileError("read-tier gemini-local prompt did not pin its read-only tool allow-list")

    pm_web_request = adapter.AgentAdapterRequest(
        building_id="agent-web-tier-pm-probe",
        agent_object_ref="agent-object:pm-lead",
        adapter_ref=adapter_constants.ADAPTER_CLAUDE_LOCAL,
        brick_instance_ref="brick-live-context",
        next_brick_instance_ref="brick-design",
        tool_policy_refs=(
            adapter_constants.LEADER_COORDINATION_TOOL_POLICY_REF,
            adapter_constants.READ_WRITE_TOOL_POLICY_REF,
            adapter_constants.WEB_CAPABLE_TOOL_POLICY_REF,
        ),
        agent_instruction_packet=pm_packet,
    )
    pm_claude_knobs = adapter_local_cli._claude_cli_invocation(pm_web_request)
    pm_claude_tools = [tool.strip() for tool in pm_claude_knobs["tools"].split(",") if tool.strip()]
    if "WebFetch" not in pm_claude_tools:
        raise ProfileError("claude-local web-capable PM request did not project WebFetch")
    if "WebSearch" not in pm_claude_tools:
        raise ProfileError("claude-local web-capable PM request did not project WebSearch")
    pm_codex_request = adapter.AgentAdapterRequest(
        building_id="agent-web-tier-codex-probe",
        agent_object_ref="agent-object:pm-lead",
        adapter_ref=adapter_constants.ADAPTER_CODEX_LOCAL,
        brick_instance_ref="brick-live-context",
        next_brick_instance_ref="brick-design",
        tool_policy_refs=pm_web_request.tool_policy_refs,
        agent_instruction_packet=pm_packet,
    )
    pm_codex_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            pm_codex_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    if not any("Web NOT available on this adapter" in rule for rule in pm_codex_prompt.get("rules", [])):
        raise ProfileError("codex-local web-capable request did not document web as unavailable")
    if pm_codex_prompt.get("native_grant", {}).get("web_requested") is not True:
        raise ProfileError("codex-local web-capable prompt did not preserve web_requested evidence")

    pm_gemini_request = adapter.AgentAdapterRequest(
        building_id="agent-web-tier-gemini-probe",
        agent_object_ref="agent-object:pm-lead",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-live-context",
        next_brick_instance_ref="brick-design",
        tool_policy_refs=pm_web_request.tool_policy_refs,
        agent_instruction_packet=pm_packet,
    )
    gemini_allow, gemini_deny = adapter_grant_policy._gemini_admin_policy_partition_for_request(pm_gemini_request)
    if "web_fetch" not in gemini_allow or "google_web_search" not in gemini_allow:
        raise ProfileError("gemini-local web-capable request did not allow web tools")
    if "run_shell_command" not in gemini_deny or "write_file" not in gemini_deny:
        raise ProfileError("gemini-local web-capable request did not deny residual write/shell tools")
    web_tool_payload = json.dumps(
        {
            "response": "web tools accepted",
            "stats": {"tools": {"totalCalls": 1, "byName": {"web_fetch": 1}}},
        }
    )
    # Smith 0623 LOCK (move+record only): a non-granted tool no longer refuses the
    # payload. The read-only fallback returns the real answer AND records web_fetch
    # as an observed non-granted tool.
    fallback_response, fallback_tools = adapter_local_cli._extract_gemini_response(web_tool_payload)
    if fallback_response != "web tools accepted":
        raise ProfileError("gemini-local read-only fallback dropped the real answer for web_fetch")
    if "web_fetch" not in fallback_tools:
        raise ProfileError(
            "gemini-local non-web extraction did not RECORD ungranted web_fetch as an "
            "observed non-granted tool"
        )
    granted_response, granted_tools = adapter_local_cli._extract_gemini_response(
        web_tool_payload,
        allowed_tool_names=adapter_grant_policy._gemini_allowed_tool_names_for_request(pm_gemini_request),
    )
    if granted_response != "web tools accepted":
        raise ProfileError("gemini-local web-capable extraction did not accept request-threaded web_fetch")
    if granted_tools:
        raise ProfileError(
            "gemini-local web-granted request wrongly recorded an observed non-granted "
            f"tool: {granted_tools!r}"
        )

    gemini_cli_capture: dict[str, Any] = {}

    def _gemini_readonly_runner(
        args: Sequence[str],
        cwd: Path,
        timeout_seconds: int,
        *,
        env: Mapping[str, str] | None = None,
    ) -> Any:
        del timeout_seconds
        call = tuple(str(arg) for arg in args)
        gemini_cli_capture["args"] = call
        gemini_cli_capture["cwd"] = cwd
        gemini_cli_capture["env_home"] = (env or {}).get("HOME")
        gemini_cli_capture["env_has_api_key"] = bool(
            (env or {}).get("GEMINI_API_KEY") or (env or {}).get("GOOGLE_API_KEY")
        )
        gemini_cli_capture["env_trust_workspace"] = (env or {}).get(
            "GEMINI_CLI_TRUST_WORKSPACE"
        )
        if "--admin-policy" in call:
            policy_path = Path(call[call.index("--admin-policy") + 1])
            gemini_cli_capture["policy_text"] = policy_path.read_text(encoding="utf-8")
        if env and env.get("HOME"):
            settings_path = Path(env["HOME"]) / ".gemini" / "settings.json"
            gemini_cli_capture["settings"] = json.loads(settings_path.read_text(encoding="utf-8"))
        return adapter.LocalCliCompleted(call, 0, '{"response": "mocked"}', "")

    saved_env = {name: os.environ.get(name) for name in adapter._GEMINI_API_KEY_ENV_VARS}
    for name in adapter._GEMINI_API_KEY_ENV_VARS:
        os.environ.pop(name, None)
    os.environ["GEMINI_API_KEY"] = "probe-key"
    try:
        adapter_local_cli._invoke_local_cli(
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_GEMINI_LOCAL],
            gemini_inspect_request,
            "prompt",
            cwd=repo,
            timeout_seconds=5,
            command_runner=_gemini_readonly_runner,
        )
    finally:
        for name in adapter._GEMINI_API_KEY_ENV_VARS:
            os.environ.pop(name, None)
            if saved_env[name] is not None:
                os.environ[name] = saved_env[name]
    gemini_args = tuple(gemini_cli_capture.get("args", ()))
    if "--approval-mode" in gemini_args:
        raise ProfileError(f"gemini-local CLI projection retained OAuth-era approval mode: {gemini_args!r}")
    if "--model" not in gemini_args or gemini_args[gemini_args.index("--model") + 1] != "gemini-3.5-flash":
        raise ProfileError(f"gemini-local read tier did not pin gemini-3.5-flash: {gemini_args!r}")
    if "--yolo" not in gemini_args:
        raise ProfileError(f"gemini-local API-key path did not enable noninteractive --yolo: {gemini_args!r}")
    if "auto_edit" in gemini_args or "yolo" in gemini_args:
        raise ProfileError(f"gemini-local CLI projection used legacy approval-mode value: {gemini_args!r}")
    if "--admin-policy" not in gemini_args:
        raise ProfileError("gemini-local CLI projection dropped read-only admin policy")
    if gemini_cli_capture.get("cwd") != repo:
        raise ProfileError("gemini-local read tier did not run from the dispatch worktree cwd")
    if not gemini_cli_capture.get("env_home"):
        raise ProfileError("gemini-local read tier did not pass a temporary HOME")
    if not gemini_cli_capture.get("env_has_api_key"):
        raise ProfileError("gemini-local read tier did not pass API-key env into subprocess")
    if gemini_cli_capture.get("env_trust_workspace") != "true":
        raise ProfileError("gemini-local read tier did not set GEMINI_CLI_TRUST_WORKSPACE=true")
    if gemini_cli_capture.get("settings") != {
        "security": {"auth": {"selectedType": "gemini-api-key"}}
    }:
        raise ProfileError("gemini-local read tier did not force temp HOME gemini-api-key auth")
    policy_text = str(gemini_cli_capture.get("policy_text", ""))
    for required_allow in (
        "read_file",
        "glob",
        "grep_search",
        "list_directory",
        "search_file_content",
        "read_many_files",
        'decision = "allow"',
        "priority = 998",
    ):
        if required_allow not in policy_text:
            raise ProfileError(
                "gemini-local read-only admin policy stopped allowing read tooling token "
                f"{required_allow!r}"
            )
    for required_deny in (
        "run_shell_command",
        "write_file",
        "replace",
        'decision = "deny"',
        "priority = 999",
    ):
        if required_deny not in policy_text:
            raise ProfileError(
                "gemini-local read-only admin policy stopped denying write/command "
                f"tooling token {required_deny!r}"
            )
    if "priority = 1000" in policy_text:
        raise ProfileError("gemini-local read-only admin policy exceeded priority ceiling")

    read_tool_payload = json.dumps(
        {
            "response": "read tools accepted",
            "stats": {
                "tools": {
                    "totalCalls": 6,
                    "byName": {
                        "read_file": 1,
                        "glob": 1,
                        # CLEAN-READTIER-0617: gemini CLI 0.46 SearchText is named
                        # grep_search (search_file_content is the legacy alias) and
                        # list_directory (ReadFolder) is a read-only browse tool;
                        # both must pass the non-read rejection set or read browse
                        # gets falsely rejected.
                        "grep_search": 1,
                        "list_directory": 1,
                        "search_file_content": 1,
                        "read_many_files": 1,
                    },
                }
            },
        }
    )
    read_response, read_tools = adapter_local_cli._extract_gemini_response(read_tool_payload)
    if read_response != "read tools accepted":
        raise ProfileError("gemini-local read tool byName payload was not accepted")
    if read_tools:
        raise ProfileError(
            f"gemini-local read-only tools wrongly recorded as non-granted: {read_tools!r}"
        )
    # Smith 0623 LOCK (move+record only): a non-read tool no longer refuses the
    # payload -- it is RECORDED as an observed non-granted tool while the answer
    # still returns.
    for forbidden_tool in ("write_file", "run_shell_command", "replace"):
        forbidden_payload = json.dumps(
            {
                "response": "non-read tool should reject",
                "stats": {"tools": {"totalCalls": 1, "byName": {forbidden_tool: 1}}},
            }
        )
        forbidden_response, forbidden_tools = adapter_local_cli._extract_gemini_response(
            forbidden_payload
        )
        if forbidden_response != "non-read tool should reject":
            raise ProfileError(
                f"gemini-local dropped the answer for non-read tool {forbidden_tool!r}"
            )
        if forbidden_tool not in forbidden_tools:
            raise ProfileError(
                f"gemini-local non-read tool record omitted {forbidden_tool!r}: "
                f"{forbidden_tools!r}"
            )

    # GEMINI-CONTROLPLANE-EXEMPT-0622: gemini's own completion/orchestration control
    # plane (complete_task, invoke_agent) has no repo/external side effect and must
    # NEVER produce a false-positive refusal/HOLD, even under the read-only fallback
    # (allowed_tool_names is None). This is the false-positive that the fix removes.
    benign_payload = json.dumps(
        {
            "response": "benign control plane accepted",
            "stats": {
                "tools": {
                    "totalCalls": 3,
                    "byName": {"complete_task": 1, "invoke_agent": 1, "read_file": 1},
                }
            },
        }
    )
    benign_response, benign_tools = adapter_local_cli._extract_gemini_response(benign_payload)
    if benign_response != "benign control plane accepted":
        raise ProfileError(
            "gemini-local benign control-plane tools (complete_task/invoke_agent) "
            "dropped the real answer"
        )
    if benign_tools:
        raise ProfileError(
            "gemini-local benign control-plane tools (complete_task/invoke_agent) "
            f"were falsely recorded as observed non-granted tools: {benign_tools!r}"
        )
    # MUTATION-RED GUARD: the benign exemption must stay BOUNDED -- a real ungranted
    # side-effecting tool bundled WITH benign control tools must STILL trip the refusal,
    # so the exemption cannot silently rot into "accept everything".
    benign_plus_write_payload = json.dumps(
        {
            "response": "benign bundled with real write must still reject",
            "stats": {
                "tools": {
                    "totalCalls": 2,
                    "byName": {"complete_task": 1, "write_file": 1},
                }
            },
        }
    )
    # Smith 0623 LOCK (move+record only): the answer always returns; the guard is
    # now that the RECORDED observed-tool set stays BOUNDED -- write_file is recorded,
    # the benign complete_task is NOT, so the exemption cannot rot into "record
    # nothing" (or "record everything").
    bundled_response, bundled_tools = adapter_local_cli._extract_gemini_response(
        benign_plus_write_payload
    )
    if bundled_response != "benign bundled with real write must still reject":
        raise ProfileError(
            "gemini-local dropped the answer for write_file bundled with benign tools"
        )
    if "write_file" not in bundled_tools:
        raise ProfileError(
            "gemini-local benign exemption widened into NOT recording an ungranted "
            "write_file (mutation-RED guard breached)"
        )
    if "complete_task" in bundled_tools:
        raise ProfileError(
            "gemini-local wrongly recorded the benign complete_task tool"
        )
    # PART 1 consistency: a web tool is a violation under the read-only fallback BUT is
    # accepted once the request's full granted set (web included) is threaded -- the
    # post-hoc must agree with the launch-time admin-policy grant.
    web_search_payload = json.dumps(
        {
            "response": "web tools accepted",
            "stats": {"tools": {"totalCalls": 1, "byName": {"google_web_search": 1}}},
        }
    )
    # Smith 0623 LOCK (move+record only): under the read-only fallback the answer
    # returns and ungranted google_web_search is RECORDED, not refused.
    web_search_response, web_search_tools = adapter_local_cli._extract_gemini_response(
        web_search_payload
    )
    if web_search_response != "web tools accepted":
        raise ProfileError(
            "gemini-local read-only fallback dropped the answer for google_web_search"
        )
    if "google_web_search" not in web_search_tools:
        raise ProfileError(
            "gemini-local ungranted google_web_search record did not name the tool"
        )
    granted_search_response, granted_search_tools = adapter_local_cli._extract_gemini_response(
        web_search_payload,
        allowed_tool_names=adapter_grant_policy._gemini_allowed_tool_names_for_request(
            pm_gemini_request
        ),
    )
    if granted_search_response != "web tools accepted":
        raise ProfileError(
            "gemini-local web-granted request rejected google_web_search the launch "
            "admin-policy allows (post-hoc inconsistent with grant)"
        )
    if granted_search_tools:
        raise ProfileError(
            "gemini-local web-granted request wrongly recorded google_web_search as "
            f"observed non-granted: {granted_search_tools!r}"
        )

    gemini_none_request = adapter.AgentAdapterRequest(
        building_id="agent-read-tier-gemini-none-probe",
        agent_object_ref="agent-object:qa",
        adapter_ref=adapter_constants.ADAPTER_GEMINI_LOCAL,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(),
        agent_instruction_packet=qa_packet,
    )
    if adapter.agent_request_read_tier(gemini_none_request):
        raise ProfileError("gemini-local none-tier request entered read tier without read-only policy")
    gemini_none_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            gemini_none_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_GEMINI_LOCAL],
        )
    )
    if "Do not use tools or hooks." not in gemini_none_prompt.get("rules", []):
        raise ProfileError("gemini-local none-tier request stopped rendering no-tools prompt")

    gemini_client_error_path = Path(tempfile.gettempdir()) / "gemini-client-error-probe.json"
    unrelated_file_body = "UNRELATED_FILE_BODY_SHOULD_NOT_ENTER_ADAPTER_ERROR_EVIDENCE"
    gemini_client_error_path.write_text(
        json.dumps(
            {
                "error": {
                    "message": unrelated_file_body,
                    "credential": "probe-credential-body-must-not-leak",
                }
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    def _gemini_nonzero_runner(
        args: Sequence[str],
        cwd: Path,
        timeout_seconds: int,
        *,
        env: Mapping[str, str] | None = None,
    ) -> Any:
        del cwd, timeout_seconds, env
        call = tuple(str(arg) for arg in args)
        if "--version" in call:
            return adapter.LocalCliCompleted(call, 0, "0.46.0", "")
        return adapter.LocalCliCompleted(
            call,
            1,
            json.dumps({"error": {"code": 404, "message": "model not found for probe"}}),
            f"Gemini CLI failed; details: {gemini_client_error_path}",
        )

    saved_env = {name: os.environ.get(name) for name in adapter._GEMINI_API_KEY_ENV_VARS}
    for name in adapter._GEMINI_API_KEY_ENV_VARS:
        os.environ.pop(name, None)
    os.environ["GEMINI_API_KEY"] = "probe-key"
    try:
        try:
            adapter_local_cli._invoke_local_cli_adapter(
                gemini_inspect_request,
                cwd=repo,
                timeout_seconds=5,
                command_runner=_gemini_nonzero_runner,
            )
        except ValueError as exc:
            nonzero_message = str(exc)
        else:
            raise ProfileError("gemini-local non-zero adapter probe did not raise")
    finally:
        gemini_client_error_path.unlink(missing_ok=True)
        for name in adapter._GEMINI_API_KEY_ENV_VARS:
            os.environ.pop(name, None)
            if saved_env[name] is not None:
                os.environ[name] = saved_env[name]
    for expected_fragment, label in (
        ("local CLI adapter command returned non-zero", "non-zero marker"),
        ("adapter_ref=adapter:gemini-local", "adapter ref"),
        ("return_code=1", "return code"),
        ("stderr_excerpt=Gemini CLI failed", "stderr excerpt"),
        ("stdout_error_excerpt=", "stdout error excerpt"),
        ("model not found for probe", "stdout error detail"),
        (f"stderr_error_path={gemini_client_error_path}", "stderr error path"),
    ):
        if expected_fragment not in nonzero_message:
            raise ProfileError(
                f"gemini-local non-zero adapter error omitted {label}: {nonzero_message!r}"
            )
    for forbidden_fragment, label in (
        ("gemini_client_error_excerpt=", "Gemini client error file excerpt"),
        (unrelated_file_body, "unrelated readable file body"),
        ("probe-credential-body-must-not-leak", "credential-looking diagnostic body"),
    ):
        if forbidden_fragment in nonzero_message:
            raise ProfileError(
                f"gemini-local non-zero adapter error included {label}: {nonzero_message!r}"
            )

    return 39


def _artifact_grounding_probe(repo: Path) -> int:
    from brick_protocol.support.connection.adapter_constants import (
        ADAPTER_LOCAL,
    )
    from brick_protocol.support.connection.agent_adapter import (
        AgentAdapterRequest,
        AgentAdapterResult,
    )
    from brick_protocol.link.movement import make_movement_fact
    from brick_protocol.link.transition import make_transition_fact
    from brick_protocol.support.operator.contracts import BuildingRunSupportResult
    from brick_protocol.support.operator.gate_sequence import (
        gate_sequence_decision_to_record,
        run_gate_sequence_policy,
    )
    from brick_protocol.support.operator.plan_validation import (
        _artifact_grounding_required_return_fields,
    )
    from brick_protocol.support.operator.run import (
        complete_agent_run_from_prepared,
        prepare_agent_run_from_step_rows,
    )
    from brick_protocol.support.recording.claims_link import (
        _gate_fact_claim_body,
        _gate_receipt_claim_body,
    )
    from brick_protocol.support.recording.building_map import BuildingMapWriteResult
    from brick_protocol.support.recording.capture import BuildingLifecycleWriteResult

    returned_field_prefix = "BrickComparisonFact.comparison_evidence.returned_field."

    def gate_returned_fields(required_public_facts: Sequence[str]) -> tuple[str, ...]:
        return tuple(
            item.removeprefix(returned_field_prefix)
            for item in required_public_facts
            if item.startswith(returned_field_prefix)
        )

    def assert_gate_fields_match_helper(
        *,
        kind: str,
        label: str,
        required_public_facts: Sequence[str],
        missing_required_facts: Sequence[str],
        expected_required_fields: Sequence[str],
        expected_missing_fields: Sequence[str],
    ) -> None:
        observed_required = gate_returned_fields(required_public_facts)
        observed_missing = gate_returned_fields(missing_required_facts)
        if observed_required != tuple(expected_required_fields):
            raise ProfileError(
                f"artifact grounding probe {kind} {label}: gate required fields "
                f"drifted from shared helper: observed {observed_required!r}, "
                f"expected {tuple(expected_required_fields)!r}"
            )
        if observed_missing != tuple(expected_missing_fields):
            raise ProfileError(
                f"artifact grounding probe {kind} {label}: gate missing fields "
                f"drifted from shared helper: observed {observed_missing!r}, "
                f"expected {tuple(expected_missing_fields)!r}"
            )

    def assert_recorded_claim_grounding_refs(
        *,
        kind: str,
        label: str,
        claim_body: Mapping[str, Any],
        grounding_field: str,
        expected_action: str,
    ) -> None:
        required_public_facts = tuple(claim_body.get("required_public_facts", ()))
        missing_required_facts = tuple(claim_body.get("missing_required_facts", ()))
        if not grounding_field:
            leaked = tuple(
                fact
                for fact in (*required_public_facts, *missing_required_facts)
                if fact.endswith(".repository_artifact_ref")
            )
            if leaked:
                raise ProfileError(
                    f"artifact grounding probe {kind} {label}: non-review claim "
                    f"recorded repository artifact ref(s) {leaked!r}"
                )
            return
        expected_public_fact = f"{returned_field_prefix}{grounding_field}"
        if expected_action == "hold":
            if expected_public_fact in required_public_facts:
                raise ProfileError(
                    f"artifact grounding probe {kind} {label}: missing repository "
                    f"artifact selector was recorded as resolvable required fact "
                    f"{expected_public_fact}"
                )
            if expected_public_fact not in missing_required_facts:
                raise ProfileError(
                    f"artifact grounding probe {kind} {label}: missing repository "
                    f"artifact selector was not recorded as demanded missing fact "
                    f"{expected_public_fact}"
                )
            return
        if expected_public_fact not in required_public_facts:
            raise ProfileError(
                f"artifact grounding probe {kind} {label}: grounded repository "
                f"artifact selector was not recorded as required fact {expected_public_fact}"
            )
        if expected_public_fact in missing_required_facts:
            raise ProfileError(
                f"artifact grounding probe {kind} {label}: grounded repository "
                f"artifact selector was also recorded missing {expected_public_fact}"
            )

    def gate_sequence_decision(
        *,
        step: Mapping[str, Any],
        prepared: Any,
        completion: Any,
        returned_value: Any,
    ) -> Any:
        adapter_request = AgentAdapterRequest(
            building_id=prepared.building_id,
            agent_object_ref=prepared.agent_object.object_ref,
            adapter_ref=ADAPTER_LOCAL,
            brick_instance_ref=prepared.brick_instance_ref,
            next_brick_instance_ref=prepared.next_brick_instance_ref,
            tool_policy_refs=prepared.agent_object.tool_policy_refs,
        )
        adapter_result = AgentAdapterResult(
            request=adapter_request,
            returned_value=returned_value,
        )
        step_result = BuildingRunSupportResult(
            building_id=prepared.building_id,
            preparation=prepared,
            adapter_result=adapter_result,
            completion=completion,
            lifecycle_write=BuildingLifecycleWriteResult(root=Path(), written_files=()),
            building_map_write=BuildingMapWriteResult(
                root=Path(),
                path=Path(),
                written_files=(),
            ),
            written_files=(),
            capture_event_types=(),
            building_map_packet=completion.building_map_packet,
            proof_limits=(),
            not_proven=(),
        )
        return run_gate_sequence_policy(
            step=step,
            step_result=step_result,
            source_brick_ref=prepared.brick_instance_ref,
            target_brick_ref=prepared.next_brick_instance_ref,
        )

    def assert_completion_and_gate_sequence(
        *,
        kind: str,
        grounding_field: str,
        expected_action: str,
        prepared: Any,
        completion: Any,
        returned_value: Any,
        step: Mapping[str, Any],
    ) -> None:
        expected_required_fields = _artifact_grounding_required_return_fields(
            completion.brick_comparison.required_return_shape_evidence,
            completion.brick_comparison.required_return_fields(),
        )
        expected_missing_fields = tuple(
            field
            for field in completion.brick_comparison.missing_return_fields()
            if field in expected_required_fields
        )
        movement_gate = completion.crossing_record.movement_gate_fact
        if movement_gate is None:
            raise ProfileError(f"artifact grounding probe {kind}: missing movement gate")
        assert_gate_fields_match_helper(
            kind=kind,
            label="movement-gate",
            required_public_facts=movement_gate.required_public_facts,
            missing_required_facts=movement_gate.missing_required_facts,
            expected_required_fields=expected_required_fields,
            expected_missing_fields=expected_missing_fields,
        )
        assert_recorded_claim_grounding_refs(
            kind=kind,
            label="movement-claim",
            claim_body=_gate_fact_claim_body(movement_gate),
            grounding_field=grounding_field,
            expected_action=expected_action,
        )
        decision = gate_sequence_decision(
            step=step,
            prepared=prepared,
            completion=completion,
            returned_value=returned_value,
        )
        if decision.action != expected_action:
            raise ProfileError(
                f"artifact grounding probe {kind}: gate sequence action "
                f"{decision.action!r}, expected {expected_action!r}"
            )
        record = gate_sequence_decision_to_record(decision)
        if not isinstance(record, Mapping):
            raise ProfileError(f"artifact grounding probe {kind}: missing gate sequence record")
        gate_results = record.get("gate_results")
        if not isinstance(gate_results, list) or len(gate_results) != 1:
            raise ProfileError(
                f"artifact grounding probe {kind}: expected one gate sequence result, "
                f"observed {gate_results!r}"
            )
        gate_record = gate_results[0]
        if not isinstance(gate_record, Mapping):
            raise ProfileError(
                f"artifact grounding probe {kind}: gate sequence result is not a mapping"
            )
        gate_ref, gate_fact = decision.gate_results[0]
        assert_gate_fields_match_helper(
            kind=kind,
            label="gate-sequence-record",
            required_public_facts=tuple(gate_record.get("required_public_facts", ())),
            missing_required_facts=tuple(gate_record.get("missing_required_facts", ())),
            expected_required_fields=expected_required_fields,
            expected_missing_fields=expected_missing_fields,
        )
        assert_recorded_claim_grounding_refs(
            kind=kind,
            label="gate-receipt-claim",
            claim_body=_gate_receipt_claim_body(gate_ref, 1, gate_fact),
            grounding_field=grounding_field,
            expected_action=expected_action,
        )
        if grounding_field:
            expected_public_fact = f"{returned_field_prefix}{grounding_field}"
            required_public_facts = tuple(gate_record.get("required_public_facts", ()))
            missing_required_facts = tuple(gate_record.get("missing_required_facts", ()))
            if expected_action == "hold" and expected_public_fact not in missing_required_facts:
                raise ProfileError(
                    f"artifact grounding probe {kind}: missing artifact did not demand "
                    f"{expected_public_fact}"
                )
            if expected_action == "forward" and (
                expected_public_fact not in required_public_facts
                or expected_public_fact in missing_required_facts
            ):
                raise ProfileError(
                    f"artifact grounding probe {kind}: grounded artifact record did not "
                    f"carry resolved {expected_public_fact}"
                )
        elif any(
            field.endswith(".repository_artifact_ref")
            for field in (*expected_required_fields, *expected_missing_fields)
        ):
            raise ProfileError(
                f"artifact grounding probe {kind}: non-review shape demanded "
                "repository artifact grounding"
            )

    cases = (
        (
            "code-attack-qa",
            "agent-object:qa",
            "observed_evidence, attacked_work, checked_sources, regression_risks, "
            "negative_probe_observations, failing_or_missing_probes, boundary_violations, "
            "evidence_used, not_proven",
            {
                "observed_evidence": ["packet-only review observed"],
                "attacked_work": ["prior packet"],
                "checked_sources": ["support-packet:prior-output"],
                "regression_risks": [],
                "negative_probe_observations": [],
                "failing_or_missing_probes": [],
                "boundary_violations": [],
                "evidence_used": ["support-packet:prior-output"],
                "not_proven": [],
            },
            {
                "observed_evidence": ["repository artifact read"],
                "attacked_work": ["prior packet"],
                "checked_sources": ["brick_protocol/support/connection/agent_adapter.py:1087"],
                "regression_risks": [],
                "negative_probe_observations": [],
                "failing_or_missing_probes": [],
                "boundary_violations": [],
                "evidence_used": ["brick_protocol/support/connection/agent_adapter.py:1087"],
                "not_proven": [],
            },
            "evidence_used.repository_artifact_ref",
        ),
        (
            "design",
            "agent-object:design-lead",
            "observed_evidence, design_summary, relevant_current_structure, proposed_changes, "
            "unchanged_surfaces, axis_responsibility, invariants, edge_cases, "
            "checker_or_verifier_plan, candidate_file_changes, evidence_refs, not_proven, "
            "reading_scope_map",
            {
                "observed_evidence": ["packet-only design observed"],
                "design_summary": "probe design",
                "relevant_current_structure": ["support packet only"],
                "proposed_changes": [],
                "unchanged_surfaces": [],
                "axis_responsibility": [],
                "invariants": [],
                "edge_cases": [],
                "checker_or_verifier_plan": [],
                "candidate_file_changes": [],
                "evidence_refs": ["support-packet:design-intake"],
                "not_proven": [],
                "reading_scope_map": ["brick_protocol/support/operator/walker_kernel.py"],
            },
            {
                "observed_evidence": ["repository artifact read"],
                "design_summary": "probe design",
                "relevant_current_structure": ["brick_protocol/brick/templates/bricks/design/brick.md:20"],
                "proposed_changes": [],
                "unchanged_surfaces": [],
                "axis_responsibility": [],
                "invariants": [],
                "edge_cases": [],
                "checker_or_verifier_plan": [],
                "candidate_file_changes": [],
                "evidence_refs": ["brick_protocol/brick/templates/bricks/design/brick.md:20"],
                "not_proven": [],
                "reading_scope_map": ["brick_protocol/support/operator/walker_kernel.py"],
            },
            "evidence_refs.repository_artifact_ref",
        ),
        (
            "non-review-evidence-used",
            "agent-object:dev",
            "observed_evidence, evidence_used, not_proven",
            {
                "observed_evidence": ["ordinary evidence observed"],
                "evidence_used": ["support-packet:ordinary"],
                "not_proven": [],
            },
            {
                "observed_evidence": ["ordinary evidence observed"],
                "evidence_used": ["brick_protocol/support/connection/agent_adapter.py:1087"],
                "not_proven": [],
            },
            "",
        ),
    )

    inspected = 0
    for kind, agent_ref, required_shape, missing_return, grounded_return, grounding_field in cases:
        step_ref = f"artifact-grounding-{kind}"
        rows = [
            {
                "axis": "Brick",
                "row_ref": f"brick-row:artifact-grounding-{kind}",
                "brick_instance_ref": f"brick-artifact-grounding-{kind}",
                "brick_work_ref": f"work:artifact-grounding-{kind}",
                "work_statement": f"{kind} Brick artifact grounding probe",
                "comparison_rule": "Repo artifact grounding is required for review/design evidence.",
                "required_return_shape": required_shape,
            },
            {
                "axis": "Agent",
                "row_ref": f"agent-row:artifact-grounding-{kind}",
                "agent_object_ref": agent_ref,
            },
            {
                "axis": "Link",
                "row_ref": f"link-row:artifact-grounding-{kind}",
                "movement": "forward",
                "target_ref": f"brick-artifact-grounding-{kind}-closure",
                "declared_gate_refs": ["link-gate:default-transition"],
                "gate_sequence_policy": [
                    {
                        "gate_ref": "link-gate:default-transition",
                        "on_missing_required_facts": {
                            "action": "HOLD",
                            "required_disposition_owner": "caller-or-coo",
                            "pending_target_basis": "target_brick",
                        },
                        "on_sufficient": {"action": "forward"},
                    }
                ],
            },
        ]
        step = {"step_ref": step_ref, "rows": rows}
        fixture = {
            "building_id": step_ref,
            "step_rows": {
                "step_ref": step_ref,
                "rows": rows,
            },
        }
        prepared = prepare_agent_run_from_step_rows(fixture)
        link_fact = make_movement_fact(
            "forward",
            reason="artifact grounding checker probe",
            handoff_target_fact=f"brick:{prepared.next_brick_instance_ref}",
        )
        transition_fact = make_transition_fact(
            "forward",
            target_fact=f"brick:{prepared.next_brick_instance_ref}",
            handoff_reference=f"checker:artifact-grounding:{kind}",
        )
        missing_completion = complete_agent_run_from_prepared(
            prepared,
            returned_value=missing_return,
            link_fact=link_fact,
            transition_fact=transition_fact,
        )
        if grounding_field not in missing_completion.brick_comparison.missing_return_fields():
            if grounding_field:
                raise ProfileError(
                    f"artifact grounding probe {kind}: packet-only return did not mark "
                    f"{grounding_field} missing"
                )
        expected_missing_action = "hold" if grounding_field else "forward"
        assert_completion_and_gate_sequence(
            kind=f"{kind}:missing-return",
            grounding_field=grounding_field,
            expected_action=expected_missing_action,
            prepared=prepared,
            completion=missing_completion,
            returned_value=missing_return,
            step=step,
        )
        movement_gate = missing_completion.crossing_record.movement_gate_fact
        expected_missing_fact = (
            "BrickComparisonFact.comparison_evidence.returned_field."
            f"{grounding_field}"
        )
        if grounding_field and (
            movement_gate is None or expected_missing_fact not in movement_gate.missing_required_facts
        ):
            raise ProfileError(
                f"artifact grounding probe {kind}: Link gate did not observe missing "
                f"required fact {expected_missing_fact}"
            )

        grounded_completion = complete_agent_run_from_prepared(
            prepared,
            returned_value=grounded_return,
            link_fact=link_fact,
            transition_fact=transition_fact,
        )
        if grounding_field and grounding_field in grounded_completion.brick_comparison.missing_return_fields():
            raise ProfileError(
                f"artifact grounding probe {kind}: repository artifact ref still "
                f"marked {grounding_field} missing"
            )
        assert_completion_and_gate_sequence(
            kind=f"{kind}:grounded-return",
            grounding_field=grounding_field,
            expected_action="forward",
            prepared=prepared,
            completion=grounded_completion,
            returned_value=grounded_return,
            step=step,
        )
        grounded_gate = grounded_completion.crossing_record.movement_gate_fact
        if grounded_gate is None or grounded_gate.missing_required_facts:
            raise ProfileError(
                f"artifact grounding probe {kind}: grounded return still produced "
                f"missing_required_facts {getattr(grounded_gate, 'missing_required_facts', None)!r}"
            )
        inspected += 2
    return inspected


def run_agent_adapter_return_shape(repo: Path) -> KernelResult:
    _ensure_import_identity(repo)
    adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    adapter_constants = importlib.import_module("brick_protocol.support.connection.adapter_constants")
    adapter_grant_policy = importlib.import_module("brick_protocol.support.connection.adapter_grant_policy")
    adapter_validation = importlib.import_module("brick_protocol.support.connection.adapter_validation")
    comparison = importlib.import_module("brick_protocol.brick.comparison")
    instruction_packet = _agent_instruction_packet_probe(repo)

    required_shape = (
        "made_changes, observed_evidence, blocked_or_missing_evidence, "
        "not_proven, remaining_delta"
    )
    output_text = json.dumps(
        {
            "no_changes_reason": "probe made no file changes",
            "observed_evidence": ["probe observed adapter return extraction"],
            "blocked_or_missing_evidence": [],
            "not_proven": ["semantic correctness"],
            "remaining_delta": [],
        },
        sort_keys=True,
    )
    extracted = adapter_grant_policy._extract_required_return_fields(output_text, required_shape)
    if extracted.get("no_changes_reason") != "probe made no file changes":
        raise ProfileError("agent adapter did not preserve made_changes waiver field")

    brick_comparison = comparison.BrickComparisonFact.from_returned_value(
        work_reference="work:agent-adapter-return-shape-probe",
        required_fields=adapter._required_return_shape_fields(required_shape),
        returned_value=extracted,
        comparison_rule="Probe made_changes waiver preservation only.",
        required_return_shape_evidence=required_shape,
    )
    if "made_changes via no_changes_reason" not in brick_comparison.waived_return_fields():
        raise ProfileError("Brick comparison did not observe no_changes_reason waiver")

    request = _agent_adapter_request_instruction_packet_probe(
        adapter,
        instruction_packet,
        required_shape,
    )
    prompt = json.loads(
        adapter_grant_policy._build_prompt(
            request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    if prompt.get("return_field_waivers") != ["no_changes_reason"]:
        raise ProfileError("adapter prompt did not expose no_changes_reason waiver")
    if prompt.get("agent_instruction_packet", {}).get("kind") != "agent-instruction-packet":
        raise ProfileError("adapter prompt did not carry Agent instruction packet")
    nested_instruction = prompt.get("agent_instruction_packet", {})
    if nested_instruction.get("required_return_shape") != required_shape:
        raise ProfileError("adapter prompt Agent instruction packet did not stamp required_return_shape")
    if nested_instruction.get("required_return_labels") != [
        "made_changes",
        "observed_evidence",
        "blocked_or_missing_evidence",
        "not_proven",
        "remaining_delta",
    ]:
        raise ProfileError("adapter prompt Agent instruction packet did not stamp required_return_labels")
    transition_required_shape = (
        "observed_evidence, transition_concern_evidence, not_proven"
    )
    transition_request = _agent_adapter_request_instruction_packet_probe(
        adapter,
        instruction_packet,
        transition_required_shape,
    )
    transition_prompt = json.loads(
        adapter_grant_policy._build_prompt(
            transition_request,
            adapter._LOCAL_CLI_SPECS[adapter_constants.ADAPTER_CODEX_LOCAL],
        )
    )
    transition_prompt_text = json.dumps(transition_prompt, sort_keys=True)
    if (
        "never return an empty object {}" not in transition_prompt_text
        or
        "If transition_concern_evidence.concern_kind is verification_gap"
        not in transition_prompt_text
        or "never name a reroute-capable Brick node" not in transition_prompt_text
    ):
        raise ProfileError(
            "adapter prompt did not carry the no-concern/verification_gap transition concern rules"
        )
    no_concern_comparison = comparison.BrickComparisonFact.from_returned_value(
        work_reference="work:agent-adapter-no-concern-probe",
        required_fields=("observed_evidence", "transition_concern_evidence", "not_proven"),
        returned_value={
            "observed_evidence": ["probe observed no concern absence"],
            "not_proven": ["semantic correctness"],
        },
        comparison_rule="Probe absent transition_concern_evidence no-concern waiver only.",
        required_return_shape_evidence=transition_required_shape,
    )
    if (
        "transition_concern_evidence absent means no concern"
        not in no_concern_comparison.waived_return_fields()
    ):
        raise ProfileError(
            "Brick comparison did not waive absent transition_concern_evidence as no concern"
        )
    return_fact = importlib.import_module("brick_protocol.agent.return_fact")
    labeled_absence_claim = {
        "concern_ref": "transition-concern:absence-domain-labeled",
        "concern_kind": "verification_gap",
        "binding": False,
        "reason_refs": ["observation:absence-domain-labeled"],
        "related_boundary_refs": [],
        "not_proven": [
            "5aeaeea not found; domain: path glob project/brick-protocol/status/**/*.md; tool: rg"
        ],
    }
    try:
        return_fact.validate_transition_concern_evidence(labeled_absence_claim)
    except (TypeError, ValueError) as exc:
        raise ProfileError(
            "transition_concern_evidence rejected a domain-labeled absence claim"
        ) from exc
    unlabeled_absence_claim = dict(labeled_absence_claim)
    unlabeled_absence_claim["concern_ref"] = "transition-concern:absence-domain-unlabeled"
    unlabeled_absence_claim["not_proven"] = ["5aeaeea not found anywhere"]
    try:
        return_fact.validate_transition_concern_evidence(unlabeled_absence_claim)
    except ValueError as exc:
        if "absence claims" not in str(exc):
            raise ProfileError(
                "unlabeled absence claim rejected for the wrong reason"
            ) from exc
    else:
        raise ProfileError(
            "transition_concern_evidence admitted an absence claim without a searched domain"
        )
    effective_write_inspected = _agent_effective_write_probe(repo, adapter, instruction_packet)
    read_tier_inspected = _agent_read_tier_probe(repo, adapter)
    artifact_grounding_inspected = _artifact_grounding_probe(repo)

    # REHOME (checker consolidation): assert the FULL return-field vocabulary the
    # retiring provider_json_return_smoke profile single-sourced (several tokens
    # were pinned only there). The Agent return label/JSON field constants live in
    # brick_protocol/support/connection/agent_adapter.py; the top-level verdict keys and always
    # recursive secret keys live in brick_protocol/agent/return_fact.py and are re-exported into
    # the adapter. An absent guard fires nothing, so verify the constants directly
    # instead of leaving the vocabulary text-pinned in one retiring profile.
    _EXPECTED_RETURN_LABEL_FIELDS = (
        "blocked_or_missing_evidence",
        "made_changes",
        "not_proven",
        "observed_evidence",
        "open_questions",
        "remaining_delta",
        "review_needed",
        "transition_concern_evidence",
    )
    _EXPECTED_RETURN_JSON_FIELDS = ("transition_concern_evidence",)
    _EXPECTED_TOP_LEVEL_VERDICT_KEYS = (
        "good_enough",
        "movement_choice",
        "route_target",
        "target_ref",
    )
    _EXPECTED_ALWAYS_SECRET_KEYS = ("credential", "secret", "session", "setup_token")
    missing_label_fields = sorted(
        set(_EXPECTED_RETURN_LABEL_FIELDS) - set(adapter._RETURN_LABEL_FIELDS)
    )
    if missing_label_fields:
        raise ProfileError(
            "agent adapter _RETURN_LABEL_FIELDS missing return label field(s): "
            + ", ".join(missing_label_fields)
        )
    missing_json_fields = sorted(
        set(_EXPECTED_RETURN_JSON_FIELDS) - set(adapter._RETURN_JSON_FIELDS)
    )
    if missing_json_fields:
        raise ProfileError(
            "agent adapter _RETURN_JSON_FIELDS missing JSON return field(s): "
            + ", ".join(missing_json_fields)
        )
    missing_top_level_keys = sorted(
        set(_EXPECTED_TOP_LEVEL_VERDICT_KEYS) - set(return_fact.TOP_LEVEL_VERDICT_KEYS)
    )
    if missing_top_level_keys:
        raise ProfileError(
            "return_fact TOP_LEVEL_VERDICT_KEYS missing forbidden return key(s): "
            + ", ".join(missing_top_level_keys)
        )
    missing_secret_keys = sorted(
        set(_EXPECTED_ALWAYS_SECRET_KEYS) - set(return_fact.ALWAYS_SECRET_KEYS)
    )
    if missing_secret_keys:
        raise ProfileError(
            "return_fact ALWAYS_SECRET_KEYS missing recursive secret key(s): "
            + ", ".join(missing_secret_keys)
        )
    if set(adapter._TOP_LEVEL_VERDICT_KEYS) != set(return_fact.TOP_LEVEL_VERDICT_KEYS):
        raise ProfileError(
            "agent adapter _TOP_LEVEL_VERDICT_KEYS drifted from "
            "return_fact TOP_LEVEL_VERDICT_KEYS"
        )
    if set(adapter._ALWAYS_SECRET_KEYS) != set(return_fact.ALWAYS_SECRET_KEYS):
        raise ProfileError(
            "agent adapter _ALWAYS_SECRET_KEYS drifted from "
            "return_fact ALWAYS_SECRET_KEYS"
        )
    try:
        adapter_validation._validate_returned_payload(
            "returned",
            {"observed_evidence": [{"checker_profile_run_results": {"pass": 5, "fail": 0}}]},
        )
    except ValueError as exc:
        raise ProfileError(
            "agent adapter rejected nested natural evidence keys pass/fail"
        ) from exc
    nested_output_text = (
        "provider preface\n"
        "```json\n"
        + json.dumps(
            {
                "observed_evidence": {
                    "profile": {"checker_profile_run_results": {"pass": 5, "fail": 0}},
                    "nested_list": ["alpha", {"nested": ["beta", {"gamma": "delta"}]}],
                },
                "not_proven": {
                    "runtime": {"provider": "not exercised"},
                },
            },
            sort_keys=True,
        )
        + "\n```"
    )
    nested_extracted = adapter_grant_policy._extract_required_return_fields(
        nested_output_text,
        "observed_evidence, not_proven",
    )
    if nested_extracted.get("observed_evidence") != [
        '["alpha",{"nested":["beta",{"gamma":"delta"}]}]',
        '{"checker_profile_run_results":{"fail":0,"pass":5}}',
    ]:
        raise ProfileError(
            "agent adapter did not preserve nested mapping/list observed_evidence "
            f"as deterministic text, observed {nested_extracted.get('observed_evidence')!r}"
        )
    if nested_extracted.get("not_proven") != ['{"provider":"not exercised"}']:
        raise ProfileError(
            "agent adapter did not preserve nested mapping/list not_proven "
            f"as deterministic text, observed {nested_extracted.get('not_proven')!r}"
        )
    # REDO (Smith 0623 struct-surgery): a top-level verdict key is NO LONGER a HOLD.
    # The payload walker quarantines it -- it must NOT raise and must REPORT the raw
    # key name. connect_agent_brain STRIPS the key (return-shaping) and exposes the
    # raw key name on the adapter side-channel; brick_protocol/support/recording records the
    # ignored_forbidden_return_key fact (the adapter records nothing).
    try:
        ignored = adapter_validation._validate_returned_payload("returned", {"success": True})
    except ValueError as exc:
        raise ProfileError(
            "agent adapter halted on a top-level verdict key instead of "
            "quarantining it (move+record only)"
        ) from exc
    if "success" not in ignored:
        raise ProfileError(
            "agent adapter did not quarantine the top-level verdict key 'success' "
            f"as a recorded fact, observed {ignored!r}"
        )
    # KEEP: nested raw secret text STILL hard-raises (credential egress is a real
    # stop the worktree does not soften).
    try:
        adapter_validation._validate_returned_payload(
            "returned",
            {"e": [{"x": "Bearer ghp_fakesecret123"}]},
        )
    except ValueError:
        pass
    else:
        raise ProfileError("agent adapter admitted nested raw secret text")

    proof_obligation_inspected = _proof_obligation_pipeline_probe(repo)
    admission_gate_live_walk_inspected = _assert_admission_gate_live_walk(
        importlib.import_module("brick_protocol.support.operator.run"),
        repo,
    )

    return KernelResult(
        check_id="agent_adapter_return_shape",
        inspected=12
        + effective_write_inspected
        + read_tier_inspected
        + artifact_grounding_inspected
        + proof_obligation_inspected
        + admission_gate_live_walk_inspected,
        output=(
            "agent adapter return shape passed: no_changes_reason waiver "
            "extraction, Brick comparison waiver, prompt projection, runtime "
            "Agent instruction packet rendering, and AgentAdapterRequest "
            "injection plus effective_write, read-tier rendering, tier-safety, "
            "artifact-grounding, proof-obligation, admission-gate live-walk, "
            "absence-claim domain labeling, and deterministic nested list-field "
            "normalization probes inspected."
        ),
    )


def _proof_obligation_pipeline_probe(repo: Path) -> int:
    _ensure_import_identity(repo)
    comparison = importlib.import_module("brick_protocol.brick.comparison")
    proof_observation = importlib.import_module("brick_protocol.support.operator.proof_observation")
    plan_validation = importlib.import_module("brick_protocol.support.operator.plan_validation")
    agent_adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    link_gate = importlib.import_module("brick_protocol.link.gate")
    run_module = importlib.import_module("brick_protocol.support.operator.run")
    walker_concern = importlib.import_module(
        "brick_protocol.support.operator.walker_transition_concern"
    )

    sentinel = object()
    if proof_observation._adapter_result_with_proof_observation(
        sentinel,
        (),
        adapter_cwd=repo,
    ) is not sentinel:
        raise ProfileError("proof observation without obligations did not preserve object identity")

    adapter_result = agent_adapter.AgentAdapterResult(
        request=SimpleNamespace(),
        returned_value={"mutation_red_runs": []},
    )
    with tempfile.TemporaryDirectory(prefix="bp-proof-mutation-red-") as tmpdir:
        mutated_marker = Path(tmpdir) / "mutated.txt"
        mutation_command = (
            "python3 -c \"from pathlib import Path; Path("
            + repr(str(mutated_marker))
            + ").write_text('bad')\""
        )
        observed_mutation = proof_observation._adapter_result_with_proof_observation(
            adapter_result,
            [{"kind": "mutation_red", "command": mutation_command}],
            adapter_cwd=repo,
        )
        if mutated_marker.exists():
            raise ProfileError("mutation_red proof obligation was executed by support")
    if observed_mutation.returned_value.get("observed_proof_runs") != []:
        raise ProfileError("mutation_red proof obligation produced an executed proof run")
    mutation_red = comparison.compare_proof_runs_to_declared_obligations(
        observed_mutation.returned_value.get("observed_proof_runs", []),
        [{"kind": "mutation_red", "command": mutation_command}],
        returned_value=observed_mutation.returned_value,
    )
    if "mutation_red_missing_or_malformed_fields" not in mutation_red:
        raise ProfileError(
            f"malformed mutation_red return was not bucketed, observed {mutation_red!r}"
        )

    with tempfile.TemporaryDirectory(prefix="bp-proof-observation-") as tmpdir:
        observed = proof_observation._run_proof_obligation(
            {"command": "python3 -c 'import sys; sys.exit(1)'", "expect_rc": 0},
            cwd=Path(tmpdir),
        )
    buckets = comparison.compare_proof_runs_to_declared_obligations(
        [observed],
        [{"command": observed["command"], "expect_rc": 0}],
    )
    if "proof_run_expect_rc_mismatch" not in buckets:
        raise ProfileError(f"proof rc mismatch was not bucketed, observed {buckets!r}")
    duplicate = comparison.compare_proof_runs_to_declared_obligations(
        [{"command": "cmd", "rc": 0}, {"command": "cmd", "rc": 1}],
        [{"command": "cmd", "expect_rc": 0}, {"command": "cmd", "expect_rc": 1}],
    )
    if duplicate:
        raise ProfileError(
            "multi-run per-command proof grouping did not consume runs independently: "
            f"{duplicate!r}"
        )
    unrun = comparison.compare_proof_runs_to_declared_obligations(
        [],
        [{"command": "python3 -c 'print(1)'", "expect_rc": 0}],
    )
    if "proof_obligation_unrun" not in unrun:
        raise ProfileError(f"unrun proof obligation was not bucketed, observed {unrun!r}")

    base = comparison.BrickComparisonFact.from_returned_value(
        work_reference="proof-obligation-probe",
        required_fields=("observed_evidence",),
        returned_value={
            "observed_evidence": [],
            "observed_proof_runs": [observed],
            "made_changes": True,
            "worktree_observation": {"observed_changed_files": []},
        },
        comparison_rule="Probe proof obligation comparison only.",
        required_return_shape_evidence="observed_evidence",
    )
    no_declared = comparison.apply_proof_obligation_comparison(
        base,
        returned_value={"observed_evidence": [], "observed_proof_runs": [observed]},
        declared_obligations=[],
    )
    if no_declared is not base:
        raise ProfileError("proof comparison without declarations changed the comparison object")
    no_declared_prepared = SimpleNamespace(
        building_id="proof-obligation-no-declared-building",
        brick_instance_ref="brick-proof-obligation-no-declared-build",
        brick_work=SimpleNamespace(
            work_statement="proof-obligation-no-declared-probe",
            comparison_rule="Probe no-declared proof obligation comparison only.",
            required_return_shape="observed_evidence",
        ),
        step_rows=SimpleNamespace(
            step_ref="proof-obligation-no-declared-build",
            brick_row={},
            link_row={"declared_gate_refs": ["link-gate:default-transition"]},
        ),
    )
    no_declared_return = {
        "observed_evidence": ["no declared proof obligations"],
        "observed_proof_runs": [observed],
    }
    no_declared_comparison_before = comparison.BrickComparisonFact.from_returned_value(
        work_reference=no_declared_prepared.brick_work.work_statement,
        required_fields=link_gate.gate_required_return_fields(
            ("link-gate:default-transition",),
            ("observed_evidence",),
        ),
        returned_value=no_declared_return,
        comparison_rule=no_declared_prepared.brick_work.comparison_rule,
        required_return_shape_evidence=no_declared_prepared.brick_work.required_return_shape,
        forbidden_shortcut_evidence=(
            "brick_protocol/support/run did not classify Agent return",
            "brick_protocol/support/run did not judge success or quality",
            "brick_protocol/support/run used caller-supplied Link facts",
        ),
    )
    no_declared_plan_validation = plan_validation._comparison_fact_from_observation(
        no_declared_prepared,
        None,
        returned_value=no_declared_return,
    )
    no_declared_gate_before = link_gate.evaluate_declared_movement_gate(
        gate_refs=("link-gate:default-transition",),
        required_return_fields=no_declared_comparison_before.required_return_fields(),
        missing_return_fields=no_declared_comparison_before.missing_return_fields(),
        observed_match_kind=no_declared_comparison_before.observed_match_kind,
        human_review_present=False,
        override_present=False,
        base_required_return_fields=no_declared_comparison_before.required_return_fields(),
        checked_public_fact="brick-comparison:no-declared-proof-probe",
        evidence_reference="brick-comparison:no-declared-proof-probe",
    )
    no_declared_gate_after = link_gate.evaluate_declared_movement_gate(
        gate_refs=("link-gate:default-transition",),
        required_return_fields=no_declared_plan_validation.required_return_fields(),
        missing_return_fields=no_declared_plan_validation.missing_return_fields(),
        observed_match_kind=no_declared_plan_validation.observed_match_kind,
        human_review_present=False,
        override_present=False,
        base_required_return_fields=no_declared_plan_validation.required_return_fields(),
        checked_public_fact="brick-comparison:no-declared-proof-probe",
        evidence_reference="brick-comparison:no-declared-proof-probe",
    )
    no_declared_before_bytes = _json_probe_bytes(
        {
            "comparison": _comparison_probe_record(no_declared_comparison_before),
            "gate": _gate_probe_record(no_declared_gate_before),
        }
    )
    no_declared_after_bytes = _json_probe_bytes(
        {
            "comparison": _comparison_probe_record(no_declared_plan_validation),
            "gate": _gate_probe_record(no_declared_gate_after),
        }
    )
    if no_declared_after_bytes != no_declared_before_bytes:
        raise ProfileError(
            "undeclared proof_obligations changed plan_validation/comparison/gate bytes: "
            f"before={no_declared_before_bytes!r} after={no_declared_after_bytes!r}"
        )
    applied = comparison.apply_proof_obligation_comparison(
        base,
        returned_value={
            "observed_evidence": [],
            "observed_proof_runs": [observed],
            "made_changes": True,
            "worktree_observation": {"observed_changed_files": []},
        },
        declared_obligations=[{"command": observed["command"], "expect_rc": 0}],
    )
    missing = applied.missing_return_fields()
    if "proof_obligation.proof_run_expect_rc_mismatch" not in missing:
        raise ProfileError("proof mismatch did not become a gate-visible missing_return_field")
    if "proof_obligation.made_changes_claim_without_observed_change" not in missing:
        raise ProfileError("made_changes contradiction did not become declaration-gated missing fact")
    prepared = SimpleNamespace(
        building_id="proof-obligation-building",
        brick_instance_ref="brick-proof-obligation-build",
        brick_work=SimpleNamespace(
            work_statement="proof-obligation-probe",
            comparison_rule="Probe proof obligation comparison only.",
            required_return_shape="observed_evidence",
        ),
        step_rows=SimpleNamespace(
            step_ref="proof-obligation-build",
            brick_row={
                "proof_obligations": [
                    {"command": observed["command"], "expect_rc": 0},
                    {"kind": "mutation_red", "command": mutation_command},
                ],
            },
            link_row={"declared_gate_refs": ["link-gate:default-transition"]},
        ),
    )
    through_plan_validation = plan_validation._comparison_fact_from_observation(
        prepared,
        None,
        returned_value={
            "observed_evidence": [],
            "observed_proof_runs": [observed],
            "mutation_red_runs": [{"red_cmd": mutation_command, "red_rc": "1"}],
        },
    )
    if (
        "proof_obligation.proof_run_expect_rc_mismatch"
        not in through_plan_validation.missing_return_fields()
        or "proof_obligation.mutation_red_missing_or_malformed_fields"
        not in through_plan_validation.missing_return_fields()
    ):
        raise ProfileError("plan_validation did not connect proof observations to comparison facts")
    proof_gate = link_gate.evaluate_declared_movement_gate(
        gate_refs=("link-gate:default-transition",),
        required_return_fields=through_plan_validation.required_return_fields(),
        missing_return_fields=through_plan_validation.missing_return_fields(),
        observed_match_kind=through_plan_validation.observed_match_kind,
        human_review_present=False,
        override_present=False,
        base_required_return_fields=through_plan_validation.required_return_fields(),
        checked_public_fact="brick-comparison:proof-probe",
        evidence_reference="brick-comparison:proof-probe",
    )
    if proof_gate is None or not proof_gate.missing_required_facts:
        raise ProfileError("default-transition gate did not consume proof missing facts")
    malformed_plan = _proof_obligation_linear_plan(
        command=mutation_command,
        kind="mutation_red",
        building_id="proof-obligation-malformed-e2e",
    )

    def _malformed_mutation_red_callable(request: Any) -> Mapping[str, Any]:
        return {
            "observed_evidence": ["malformed mutation_red e2e probe"],
            "mutation_red_runs": [{"red_cmd": mutation_command, "red_rc": "1"}],
        }

    with tempfile.TemporaryDirectory(prefix="bp-proof-malformed-e2e-") as tmpdir:
        malformed_result = run_module.run_building_plan(
            malformed_plan,
            output_root=Path(tmpdir),
            overwrite_existing=True,
            local_callables={
                "callable:local:agent-invoke0-smoke": _malformed_mutation_red_callable
            },
            adapter_cwd=repo,
            adapter_timeout_seconds=30,
        )
    if len(malformed_result.step_results) != 1:
        raise ProfileError("malformed mutation_red e2e fixture did not run exactly one step")
    malformed_step = malformed_result.step_results[0]
    malformed_missing = malformed_step.completion.brick_comparison.missing_return_fields()
    if "proof_obligation.mutation_red_missing_or_malformed_fields" not in malformed_missing:
        raise ProfileError(
            "real adapter return -> run.py -> plan_validation did not flag malformed "
            f"mutation_red_runs ({malformed_missing!r})"
        )
    malformed_gate = malformed_step.completion.crossing_record.movement_gate_fact
    if malformed_gate is None or not any(
        "proof_obligation.mutation_red_missing_or_malformed_fields" in item
        for item in malformed_gate.missing_required_facts
    ):
        raise ProfileError(
            "real adapter return -> run.py -> plan_validation -> gate did not carry "
            "malformed mutation_red_runs missing fact"
        )
    step_result = SimpleNamespace(
        building_id=prepared.building_id,
        preparation=prepared,
        adapter_result=agent_adapter.AgentAdapterResult(
            request=SimpleNamespace(),
            returned_value={"observed_evidence": [], "observed_proof_runs": [observed]},
        ),
        completion=SimpleNamespace(brick_comparison=through_plan_validation),
    )
    concern_observation = walker_concern._transition_concern_observation_from_step_result(
        step_result
    )
    if concern_observation.concern is None:
        raise ProfileError("proof mismatch did not produce a reroute-eligible transition concern")
    classification = walker_concern._classify_reroute_target(
        concern_observation.concern,
        declared_bricks={"brick-proof-obligation-build"},
        source_brick_ref="brick-proof-obligation-build",
    )
    if classification.kind != "single" or classification.target != "brick-proof-obligation-build":
        raise ProfileError(
            "machine-authored proof concern did not resolve to the declared source Brick: "
            f"{classification!r}"
        )
    return 15


def _json_probe_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _comparison_probe_record(value: Any) -> Mapping[str, Any]:
    return {
        "work_reference": value.work_reference,
        "comparison_evidence": list(value.comparison_evidence),
        "observed_match_kind": value.observed_match_kind,
        "comparison_rule": value.comparison_rule,
        "required_return_shape_evidence": value.required_return_shape_evidence,
        "forbidden_shortcut_evidence": list(value.forbidden_shortcut_evidence),
    }


def _gate_probe_record(value: Any) -> Mapping[str, Any] | None:
    if value is None:
        return None
    return {
        "stage": value.stage,
        "sufficiency": value.sufficiency,
        "checked_public_fact": value.checked_public_fact,
        "required_public_facts": list(value.required_public_facts),
        "missing_required_facts": list(value.missing_required_facts),
        "reason": value.reason,
        "evidence_reference": value.evidence_reference,
    }


def _admission_gate_live_walk_plan(
    *,
    building_id: str,
    declared_gate_refs: Sequence[str],
) -> Mapping[str, Any]:
    step_ref = f"{building_id}-work"
    brick_ref = f"brick-{building_id}-work"
    edge_ref = f"edge:{step_ref}-to-boundary"
    return {
        "plan_ref": f"building-plan:{building_id}",
        "owner_axis": "Brick",
        "building_id": building_id,
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": ["checker admission-gate live-walk fixture support evidence only"],
        "not_proven": ["semantic correctness of checker fixture returns"],
        "execution_order": [step_ref],
        "brick_steps": [
            {
                "step_ref": step_ref,
                "completion_edge_ref": edge_ref,
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": f"brick-row:{step_ref}",
                        "brick_work_ref": f"work:{step_ref}",
                        "brick_instance_ref": brick_ref,
                        "work_statement": "admission gate live walk probe",
                        "required_return_shape": "observed_evidence, not_proven",
                        "comparison_rule": "Probe declared gate evaluation on graph walk.",
                    },
                    {
                        "axis": "Agent",
                        "row_ref": f"agent-row:{step_ref}",
                        "agent_object_ref": "agent-object:dev",
                    },
                ],
            }
        ],
        "link_edges": [
            {
                "edge_ref": edge_ref,
                "source_step_ref": step_ref,
                "rows": [
                    {
                        "axis": "Link",
                        "row_ref": f"link-row:{edge_ref}",
                        "movement": "forward",
                        "target_ref": f"building-boundary:{building_id}",
                        "building_lifecycle": {
                            "state": "closed",
                            "reason": "admission gate live walk probe closed",
                        },
                        "declared_gate_refs": list(declared_gate_refs),
                    },
                ],
            }
        ],
    }


def _assert_admission_gate_live_walk(run_module: Any, repo: Path) -> int:
    def _callable(_request: Any) -> Mapping[str, Any]:
        return {
            "observed_evidence": ["admission gate live walk fixture return"],
            "not_proven": ["checker fixture semantic correctness"],
        }

    def _run(building_id: str, gate_refs: Sequence[str]) -> Any:
        with tempfile.TemporaryDirectory(prefix=f"bp-{building_id}-") as tmpdir:
            result = run_module.run_building_plan(
                _admission_gate_live_walk_plan(
                    building_id=building_id,
                    declared_gate_refs=gate_refs,
                ),
                output_root=Path(tmpdir),
                overwrite_existing=True,
                local_callables={
                    "callable:local:agent-invoke0-smoke": _callable,
                },
                adapter_cwd=repo,
                adapter_timeout_seconds=30,
            )
        if len(result.step_results) != 1:
            raise ProfileError(
                f"admission gate live-walk probe {building_id}: expected one step, "
                f"observed {len(result.step_results)}"
            )
        gate = result.step_results[0].completion.crossing_record.movement_gate_fact
        if gate is None:
            raise ProfileError(
                f"admission gate live-walk probe {building_id}: missing movement GateFact"
            )
        return gate

    strict_gate = _run(
        "admission-gate-live-strict",
        ("link-gate:default-transition", "link-gate:strict"),
    )
    strict_missing = tuple(strict_gate.missing_required_facts)
    for field in (
        "blocked_or_missing_evidence",
        "remaining_delta",
        "proof_limits",
    ):
        public_fact = f"BrickComparisonFact.comparison_evidence.returned_field.{field}"
        if public_fact not in strict_missing:
            raise ProfileError(
                "admission gate live-walk probe: strict declared graph did not "
                f"record missing public fact {public_fact}"
            )
    if "link-gate:strict" not in strict_gate.reason:
        raise ProfileError(
            "admission gate live-walk probe: strict movement GateFact reason did "
            "not name the declared strict gate"
        )

    default_gate = _run(
        "admission-gate-live-default",
        ("link-gate:default-transition",),
    )
    default_missing = tuple(default_gate.missing_required_facts)
    if any(item in default_missing for item in strict_missing):
        raise ProfileError(
            "admission gate live-walk probe: default-only graph recorded strict "
            f"missing facts {default_missing!r}"
        )
    if "link-gate:strict" in default_gate.reason:
        raise ProfileError(
            "admission gate live-walk probe: default-only graph mentioned strict gate"
        )
    return 2


def _proof_obligation_linear_plan(
    *,
    command: str,
    kind: str,
    building_id: str,
) -> Mapping[str, Any]:
    step_ref = "proof-obligation-build"
    brick_ref = "brick-proof-obligation-build"
    edge_ref = "edge:proof-obligation-build-to-boundary"
    return {
        "plan_ref": f"building-plan:{building_id}",
        "owner_axis": "Brick",
        "building_id": building_id,
        "plan_shape": "graph",
        "selected_adapter_ref": "adapter:local",
        "proof_limits": ["checker proof-obligation fixture support evidence only"],
        "not_proven": ["semantic correctness of proof obligation command"],
        "execution_order": [step_ref],
        "brick_steps": [
            {
                "step_ref": step_ref,
                "completion_edge_ref": edge_ref,
                "rows": [
                    {
                        "axis": "Brick",
                        "row_ref": f"brick-row:{step_ref}",
                        "brick_work_ref": f"work:{step_ref}",
                        "brick_instance_ref": brick_ref,
                        "work_statement": "proof obligation e2e probe",
                        "required_return_shape": "observed_evidence",
                        "comparison_rule": "Probe malformed mutation_red e2e flow only.",
                        "proof_obligations": [
                            {"kind": kind, "command": command, "expect_rc": 0}
                        ],
                    },
                    {
                        "axis": "Agent",
                        "row_ref": f"agent-row:{step_ref}",
                        "agent_object_ref": "agent-object:dev",
                    },
                ],
            }
        ],
        "link_edges": [
            {
                "edge_ref": edge_ref,
                "source_step_ref": step_ref,
                "rows": [
                    {
                        "axis": "Link",
                        "row_ref": f"link-row:{edge_ref}",
                        "movement": "forward",
                        "target_ref": "building-boundary:proof-obligation-e2e",
                        "building_lifecycle": {
                            "state": "closed",
                            "reason": "proof obligation e2e probe closed",
                        },
                        "declared_gate_refs": ["link-gate:default-transition"],
                    },
                ],
            }
        ],
    }


def _run_agent_adapter_return_shape_profile(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "brick_protocol/support/checkers/check_profile.py",
            "--repo",
            ".",
            "--profile",
            "agent_axis_behavioral",
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def probe_mutation_red(repo: Path) -> list[str]:
    source = Path(__file__).resolve()
    original = source.read_text(encoding="utf-8")
    needle = "def run_agent_adapter_return_shape(repo: Path) -> KernelResult:"
    poisoned = "def run_agent_adapter_return_shape_disabled(repo: Path) -> KernelResult:"
    if needle not in original:
        raise ProfileError("agent_adapter_return_shape mutation probe could not find entrypoint")

    backup = tempfile.NamedTemporaryFile(
        prefix=".agent-adapter-return-shape-check.",
        suffix=".bak",
        dir=source.parent,
        delete=False,
    )
    backup_path = Path(backup.name)
    backup.close()
    shutil.copyfile(source, backup_path)
    try:
        source.write_text(original.replace(needle, poisoned, 1), encoding="utf-8")
        red = _run_agent_adapter_return_shape_profile(repo)
        if red.returncode == 0:
            raise ProfileError(
                "agent_adapter_return_shape mutation probe did not turn agent_axis_behavioral RED"
            )
    finally:
        shutil.copyfile(backup_path, source)
        backup_path.unlink(missing_ok=True)

    green = _run_agent_adapter_return_shape_profile(repo)
    if green.returncode != 0:
        excerpt = "\n".join(green.stdout.splitlines()[-20:])
        raise ProfileError(
            "agent_adapter_return_shape mutation probe restored source but profile "
            f"remained RED:\n{excerpt}"
        )

    return [
        "agent adapter return-shape mutation RED probe passed: disabling the "
        "moved run_agent_adapter_return_shape entrypoint made check_profile.py "
        "--profile agent_axis_behavioral exit non-zero, then restoring the "
        "temp-backed self file returned the profile to exit 0."
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Support-evidence checker leaf for agent adapter return shape."
    )
    parser.add_argument("--repo", default=None)
    parser.add_argument(
        "--probe-mutation-red",
        action="store_true",
        help=(
            "temporarily disable this leaf's moved run_agent_adapter_return_shape "
            "entrypoint, assert agent_axis_behavioral exits RED, restore from a "
            "temp backup, then assert the profile is GREEN"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = (
            probe_mutation_red(repo)
            if args.probe_mutation_red
            else [run_agent_adapter_return_shape(repo).output]
        )
    except ProfileError as exc:
        print("agent adapter return shape rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
