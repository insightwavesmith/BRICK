"""In-process kernel-check bodies + axis-vocab drift scan + subprocess shim.

Lifted verbatim from check_profile.py (P3a behavior-preserving decomposition).
Holds the kernel-check implementations the profile runner's run_kernel_check
dispatches to (axis_vocab_drift, building_map_graph, agent_adapter_return_shape,
reporter_notification_projection) plus the in-process call_main shim. Support
checker mechanics only: it derives/observes evidence shapes; it authors no axis
crossing and decides nothing.
"""

from __future__ import annotations

import argparse
import ast
import base64
import contextlib
import hashlib
import hmac
import importlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from support.checkers.lib.yaml_subset import (
    KernelResult,
    ProfileError,
    _ensure_import_identity,
    to_posix,
    to_repo_path,
)
from support.checkers.lib.provider_preflight_check import (
    _PROVIDER_PREFLIGHT_AUTHED_LITERALS,
    _PROVIDER_PREFLIGHT_REQUIRED_KEYS,
    _provider_preflight_assert_shape,
    run_provider_preflight,
)
from support.checkers.lib.onboard_smoke_check import (
    _ONBOARD_SMOKE_REQUIRED_KEYS,
    run_onboard_smoke,
    _onboard_smoke_assert_shape,
)


from support.checkers.lib.axis_vocab_drift_check import (
    _AXIS_VOCAB_EXPECTED_MOVEMENT,
    _AXIS_VOCAB_EXPECTED_DISPOSITION_ACTIONS,
    _AXIS_VOCAB_EXPECTED_DISPOSITION_OWNERS,
    _AXIS_VOCAB_EXPECTED_PROGRESS_STATES,
    _AXIS_VOCAB_EXPECTED_AUTHOR_PREFIXES,
    _AXIS_VOCAB_REQUIRED_TRANSITION_KEYS,
    _AXIS_VOCAB_CONCERN_KIND_SOURCE,
    _AXIS_VOCAB_CONCERN_KIND_CONST,
    _AXIS_VOCAB_CONCERN_KIND_DOC,
    _AXIS_VOCAB_CONCERN_KIND_DOC_HEADER,
    _AXIS_VOCAB_EXPECTED_ADAPTER_REFS,
    _AXIS_VOCAB_RETIRED_WRITE_ADAPTER_REFS,
    _AXIS_VOCAB_DOC_PATHS,
    _AXIS_VOCAB_MOVEMENT_ENUM_ALLOWLIST,
    _AXIS_VOCAB_DISPOSITION_ENUM_ALLOWLIST,
    _AXIS_VOCAB_ADAPTER_ENUM_ALLOWLIST,
    _AXIS_VOCAB_TRANSITION_AUTHOR_PREFIX_CONSUMERS,
    _AXIS_VOCAB_PYTHON_SCAN_ROOTS,
    _axis_vocab_parse_python,
    _axis_vocab_read_literal,
    _axis_vocab_all_strings,
    _axis_vocab_module_env,
    _axis_vocab_sequence,
    _axis_vocab_set,
    _axis_vocab_literal_string_set,
    _axis_vocab_import_aliases,
    _axis_vocab_absolute_import_aliases,
    _axis_vocab_assigned_names,
    _axis_vocab_name_used,
    _axis_vocab_python_files,
    _axis_vocab_scan_exact_enum_redefinitions,
    _axis_vocab_check_link_sources,
    _axis_vocab_check_transition_author_prefix_consumers,
    _axis_vocab_check_docs,
    _axis_vocab_check_agent_adapter_refs,
    _axis_vocab_doc_fenced_block,
    _axis_vocab_check_concern_kind_parity,
    run_axis_vocab_drift,
)
from support.checkers.lib.building_plan_graph_check import (
    run_building_map_graph,
    run_building_plans_boundary_sweep,
)
from support.checkers.lib.building_result_summary_check import (
    _assert_no_forbidden_summary_key,
    _init_git_repo_with_wip_anchor,
    _write_json,
    _write_jsonl,
    run_building_result_summary,
)
from support.checkers.lib.raw_evidence_stream_scrub_check import run_raw_evidence_stream_scrub
from support.checkers.lib.agent_output_text_preservation_check import (
    run_agent_output_text_preservation,
)
from support.checkers.lib.brick_cli_entrypoint_check import run_brick_cli_entrypoint_smoke
from support.checkers.lib.mcp_connect_projection_check import (
    run_claude_projection_native,
    run_codex_projection_native,
    run_connect_config_launch,
    run_mcp_stdio_smoke,
)
from support.checkers.lib.chat_session_park_check import (
    _chat_session_assert_envelope_session_key_rejects,
    _chat_session_assert_key_scan_fire,
    _chat_session_assert_undeclared_adapter_rejects,
    _chat_session_delete_work_envelope,
    _chat_session_mutate_envelope_uuid,
    _chat_session_mutate_park_as_adapter_error,
    _chat_session_park_graph_plan,
    _chat_session_probe_ulid_text,
    _chat_session_probe_uuid_text,
    _chat_session_value_only_session_rejector,
    _chat_session_write_temp_project_declaration,
    run_chat_session_park_seam,
)
from support.checkers.lib.adapter_error_check import (
    run_adapter_error_frontier_manifest_consistency,
    run_adapter_error_path_hardening,
)
from support.checkers.lib.agent_session_id_redaction_check import run_agent_session_id_redaction
from support.checkers.lib.dashboard_productization_projection_check import (
    run_dashboard_productization_projection,
)

# chat_session_park_seam facade pins retained for unchanged profiles after pure relocation:
# _chat_session_mutate_envelope_uuid / _chat_session_mutate_park_as_adapter_error /
# _chat_session_delete_work_envelope / _chat_session_assert_undeclared_adapter_rejects /
# _chat_session_assert_envelope_session_key_rejects / _chat_session_assert_key_scan_fire /
# _chat_session_value_only_session_rejector / _chat_session_probe_uuid_text /
# _chat_session_probe_ulid_text
# agent_session_id_redaction facade retained for unchanged check_profile dispatch.
# Facade text pins retained for unchanged profiles after pure relocation:
# raw_evidence_stream_scrub / brick-work.jsonl / agent-received.jsonl /
# agent-return.jsonl / agent-output-text.jsonl / adapter-error.jsonl
# agent_output_text_preservation / mutation RED observed / AgentFact.returned
# brick_cli_entrypoint_smoke / customer graph_packet may not author Brick template-owned field
# hidden _p3_easy_large_graph_packet helper / status revived legacy ~/.brick/builds
# plain CLI error leaked raw operator detail / internal/onboard route became public
# --dev-lanes became a public official build mode
# lane_return helper must stay absent/fail-closed
# support-only observation lost proof limit
# bare brick --json did not default to status
# status packet omitted adapter_boundary_matrix



@contextlib.contextmanager
def captured_output() -> Any:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        yield out, err


@contextlib.contextmanager
def patched_argv(argv: list[str]) -> Any:
    previous = sys.argv[:]
    sys.argv = argv
    try:
        yield
    finally:
        sys.argv = previous


@contextlib.contextmanager
def _without_report_grain_env() -> Any:
    previous = os.environ.pop("BRICK_REPORT_GRAIN", None)
    try:
        yield
    finally:
        if previous is not None:
            os.environ["BRICK_REPORT_GRAIN"] = previous


def call_main(check_id: str, module_name: str, argv: list[str] | None) -> KernelResult:
    module = importlib.import_module(module_name)
    with captured_output() as (out, err):
        if argv is None:
            with patched_argv([check_id]):
                code = int(module.main())
        elif check_id == "package_path_admission":
            with patched_argv([check_id] + argv):
                code = int(module.main())
        else:
            code = int(module.main(argv))
    output = (out.getvalue() + err.getvalue()).strip()
    if code != 0:
        raise ProfileError(f"kernel check {check_id} rejected evidence:\n{output}")
    return KernelResult(check_id=check_id, inspected=1, output=output)


def _minimal_reporter_packet() -> Mapping[str, Any]:
    return {
        "report_id": "reporter-negative-probe-valid",
        "report_kind": "building_frontier",
        "building_id": "probe-building",
        "portfolio_id": "",
        "observed_board_state": "observed_running",
        "trigger_event_ref": "observation:probe",
        "current_brick_ref": "brick:probe",
        "current_work_kind": "work",
        "current_lane": "worker",
        "last_completed_step_ref": "",
        "frontier_ref": "project/brick-protocol/buildings/probe#frontier:closure_pending",
        "evidence_root_refs": ["project/brick-protocol/buildings/probe"],
        "evidence_refs_present": False,
        "checker_summary_ref": "support/checkers/profiles/reporter_notification_projection.yaml",
        "required_disposition_owner": "",
        "sink_refs": ["report-sink:local-inbox"],
        "generated_at": "2026-05-31T00:00:00+00:00",
        "source_truth": False,
        "not_proven": ["negative probe"],
        "proof_limits": ["negative probe support evidence only"],
    }


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
        "allowed_paths": ["support/connection/agent_adapter.py"],
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
            cwd=repo / "support",
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
    # (by support/recording) as missing_agent_write_policy, and the building continues.
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
    # -- the disposition is RECORDED (by support/recording) as
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
        "allowed_paths": ["support/checkers/generated-probes/**"],
        "forbidden_paths": [".git/**", "agent/**", "brick/**", "link/**"],
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
    tool_policy_dir = repo / "agent" / "tool_policies"
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
                "checked_sources": ["support/connection/agent_adapter.py:1087"],
                "regression_risks": [],
                "negative_probe_observations": [],
                "failing_or_missing_probes": [],
                "boundary_violations": [],
                "evidence_used": ["support/connection/agent_adapter.py:1087"],
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
                "reading_scope_map": ["support/operator/walker_kernel.py"],
            },
            {
                "observed_evidence": ["repository artifact read"],
                "design_summary": "probe design",
                "relevant_current_structure": ["brick/templates/bricks/design/brick.md:20"],
                "proposed_changes": [],
                "unchanged_surfaces": [],
                "axis_responsibility": [],
                "invariants": [],
                "edge_cases": [],
                "checker_or_verifier_plan": [],
                "candidate_file_changes": [],
                "evidence_refs": ["brick/templates/bricks/design/brick.md:20"],
                "not_proven": [],
                "reading_scope_map": ["support/operator/walker_kernel.py"],
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
                "evidence_used": ["support/connection/agent_adapter.py:1087"],
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
    effective_write_inspected = _agent_effective_write_probe(repo, adapter, instruction_packet)
    read_tier_inspected = _agent_read_tier_probe(repo, adapter)
    artifact_grounding_inspected = _artifact_grounding_probe(repo)

    # REHOME (checker consolidation): assert the FULL return-field vocabulary the
    # retiring provider_json_return_smoke profile single-sourced (several tokens
    # were pinned only there). The Agent return label/JSON field constants live in
    # support/connection/agent_adapter.py; the top-level verdict keys and always
    # recursive secret keys live in agent/return_fact.py and are re-exported into
    # the adapter. An absent guard fires nothing, so verify the constants directly
    # instead of leaving the vocabulary text-pinned in one retiring profile.
    return_fact = importlib.import_module("brick_protocol.agent.return_fact")
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
    _EXPECTED_TOP_LEVEL_VERDICT_KEYS = ("movement_choice", "route_target", "target_ref")
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
    # raw key name on the adapter side-channel; support/recording records the
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

    return KernelResult(
        check_id="agent_adapter_return_shape",
        inspected=10
        + effective_write_inspected
        + read_tier_inspected
        + artifact_grounding_inspected
        + proof_obligation_inspected,
        output=(
            "agent adapter return shape passed: no_changes_reason waiver "
            "extraction, Brick comparison waiver, prompt projection, runtime "
            "Agent instruction packet rendering, and AgentAdapterRequest "
            "injection plus effective_write, read-tier rendering, tier-safety, "
            "artifact-grounding, proof-obligation, and deterministic nested list-field "
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
            "support/run did not classify Agent return",
            "support/run did not judge success or quality",
            "support/run used caller-supplied Link facts",
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


def _gemini_api_classify_error_kind(exc: Exception) -> str:
    """Read-only mirror of run.py._adapter_error_kind (we cannot edit run.py).

    The B2-hardened hold path classifies adapter exceptions by type/message. We
    replicate the mapping here ONLY to assert (in-process) that a gemini-api
    no-key error flows the SAME clean typed adapter-error path, never a crash.

    INTENTIONAL DIVERGENCE from run.py._adapter_error_kind (codex-review F4): the
    TimeoutExpired branch here maps to plain 'local_cli_timeout' and is NOT given
    the connect-stall split. Gemini is an HTTP API adapter with no codex
    dead-connection watchdog, so a stall-tagged TimeoutExpired can never reach it
    and 'local_cli_connect_stall' is correctly absent. Every OTHER branch mirrors
    run.py._adapter_error_kind.
    """
    message = str(exc).lower()
    if isinstance(exc, FileNotFoundError):
        return "local_cli_missing"
    if isinstance(exc, subprocess.TimeoutExpired):
        return "local_cli_timeout"
    if "non-zero" in message or "returned non-zero" in message:
        return "local_cli_nonzero"
    if "returned payload" in message or "forbidden returned" in message:
        return "adapter_return_shape_rejected"
    return "adapter_exception"


from support.checkers.lib.design_ai_text_seams_check import run_design_ai_text_seams
from support.checkers.lib.codex_connect_stall_classification_check import (
    run_codex_connect_stall_classification,
)
from support.checkers.lib.gemini_local_only_adapter_check import run_gemini_local_only_adapter
from support.checkers.lib.graph_topology_fan_barrier import run_graph_topology_fan_barrier


# FINAL architecture leaf (0630): the install_script_lint + release_export_exclusion
# cluster moved VERBATIM into the flat checker-lib sibling
# install_release_export_lint_check.py (conservation ledger
# customer-ready-final-architecture-install-release-export-lint-ledger-0630.md).
# Re-exported here so check_profile imports stay byte-identical.
from support.checkers.lib.install_release_export_lint_check import (
    _INSTALL_SCRIPT_REL,
    _RELEASE_EXPORT_REL,
    _RELEASE_EXPORT_REQUIRED_EXCLUSIONS,
    _INSTALL_SCRIPT_SECRET_PATTERNS,
    run_install_script_lint,
    _release_export_exclusions,
    _release_export_exclusion_violations,
    _release_export_exclusion_fire_probe,
    run_release_export_exclusion,
    run_release_gate_contract,
)


# FINAL architecture leaf (0630): the product no-Smith-residue scan cluster
# moved VERBATIM into the flat checker-lib sibling no_smith_residue_check.py
# (conservation ledger customer-ready-final-architecture-no-smith-residue-ledger-0630.md).
# Re-exported here so check_profile imports and the in-file _SMITH_USER_HOME_LITERAL
# call site stay byte-identical.
from support.checkers.lib.no_smith_residue_check import (
    _SMITH_USER_HOME_LITERAL,
    _SMITH_GITHUB_ORG_LITERAL,
    _SMITH_GITHUB_REPO_LITERAL,
    _NO_SMITH_RESIDUE_SURFACES,
    _no_smith_residue_text_paths,
    _no_smith_residue_allowed_org_line,
    _collect_no_smith_residue_violations,
    _copy_no_smith_residue_surfaces,
    _no_smith_residue_fire_probe,
    run_product_no_smith_residue,
)


def _minimal_operator_wake_target() -> Mapping[str, Any]:
    return {
        "target_ref": "operator-wake-target:local-active-operator",
        "target_kind": "operator_wake_local",
        "sink_ref": "report-sink:operator-wake-local",
        "delivery_mode": "local_projection",
        "side_effect_state": "none",
        "proof_limits": ["provider-neutral local wake target reference only"],
        "not_proven": [
            "operator noticed wake packet",
            "real provider thread wake behavior",
            "external side effect behavior",
        ],
    }


# Inbox-packet property tables, migrated 1:1 from the retired standing-packet
# pins of read_side_projection_boundary.yaml (json_required_paths +
# json_value_paths on the 3 dogfood status/inbox packets).
_INBOX_FRONTIER_PACKET_REQUIRED_KEYS = (
    "report_id",
    "report_kind",
    "building_id",
    "portfolio_id",
    "observed_board_state",
    "trigger_event_ref",
    "current_brick_ref",
    "current_work_kind",
    "current_lane",
    "last_completed_step_ref",
    "frontier_ref",
    "evidence_root_refs",
    "evidence_refs_present",
    "checker_summary_ref",
    "required_disposition_owner",
    "sink_refs",
    "generated_at",
    "source_truth",
    "not_proven",
    "proof_limits",
)
_OPERATOR_WAKE_PACKET_REQUIRED_KEYS = (
    "wake_packet_id",
    "report_id",
    "report_kind",
    "building_id",
    "observed_board_state",
    "evidence_root_refs",
    "operator_wake_targets",
    "source_truth",
    "not_proven",
    "proof_limits",
)


def _reporter_inbox_packet_shape_fold(
    reporter: Any,
    *,
    local_inbox_packet: Mapping[str, Any],
    wake_bus_frontier_packet: Mapping[str, Any],
    operator_wake_packet: Mapping[str, Any],
) -> None:
    """Assert the written inbox/wake packets carry the retired pins' shape."""

    for packet_label, packet in (
        ("local-inbox frontier packet", local_inbox_packet),
        ("wake-bus frontier packet", wake_bus_frontier_packet),
    ):
        for key in _INBOX_FRONTIER_PACKET_REQUIRED_KEYS:
            if key not in packet:
                raise ProfileError(f"{packet_label} is missing required key {key!r}")
        if not (isinstance(packet.get("evidence_root_refs"), list) and packet["evidence_root_refs"]):
            raise ProfileError(f"{packet_label} evidence_root_refs must be a non-empty list")
        if packet.get("observed_board_state") not in set(reporter.OBSERVED_BOARD_STATES):
            raise ProfileError(
                f"{packet_label} observed_board_state {packet.get('observed_board_state')!r} "
                "is not an admitted OBSERVED_BOARD_STATES member"
            )
        if "report-sink:local-inbox" not in (packet.get("sink_refs") or []):
            raise ProfileError(f"{packet_label} sink_refs does not name report-sink:local-inbox")
    if "report-sink:operator-wake-local" not in (
        wake_bus_frontier_packet.get("sink_refs") or []
    ):
        raise ProfileError(
            "wake-bus frontier packet sink_refs does not name report-sink:operator-wake-local"
        )
    wake_bus_targets = wake_bus_frontier_packet.get("operator_wake_targets")
    if not (isinstance(wake_bus_targets, list) and wake_bus_targets):
        raise ProfileError("wake-bus frontier packet operator_wake_targets must be non-empty")
    if any(
        target.get("sink_ref") != "report-sink:operator-wake-local"
        for target in wake_bus_targets
        if isinstance(target, Mapping)
    ):
        raise ProfileError(
            "wake-bus frontier packet operator_wake_targets[].sink_ref must be "
            "report-sink:operator-wake-local"
        )
    for key in _OPERATOR_WAKE_PACKET_REQUIRED_KEYS:
        if key not in operator_wake_packet:
            raise ProfileError(f"operator wake packet is missing required key {key!r}")
    wake_targets = operator_wake_packet.get("operator_wake_targets")
    if not (isinstance(wake_targets, list) and wake_targets):
        raise ProfileError("operator wake packet operator_wake_targets must be non-empty")
    for target in wake_targets:
        if not isinstance(target, Mapping) or target.get("delivery_mode") != "local_projection":
            raise ProfileError(
                "operator wake packet operator_wake_targets[].delivery_mode must be "
                "local_projection"
            )


def _assert_reporter_label_parity(repo: Path) -> int:
    canonical_path = repo / "support" / "operator" / "label_map.json"
    labels_js_path = repo / "support" / "dashboard" / "src" / "data" / "labels.js"
    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    if not isinstance(canonical, Mapping):
        raise ProfileError("label_map.json did not parse as a mapping")
    labels_js = labels_js_path.read_text(encoding="utf-8")
    checks = {
        "BRICK": "brick_kinds",
        "LANE": "lanes",
        "TOOL": "tool_policies",
        "MOVEMENT": "movements",
        "STATE": "states",
        "DISP": "display_states",
        "OWNER": "disposition_owners",
        "EVENT": "events",
        "OBSERVED": "observed_board_states",
        "ACTION": "actions",
    }
    inspected = 0
    for const_name, section in checks.items():
        observed = _extract_js_const_object(labels_js, const_name)
        expected = canonical.get(section)
        if observed != expected:
            raise ProfileError(
                f"label parity mismatch for {const_name}/{section}: "
                f"observed={observed!r} expected={expected!r}"
            )
        inspected += 1
    return inspected


def _assert_reporter_agent_incomplete_event_mapping(reporter: Any) -> int:
    original_observer = reporter.observe_building_frontier

    def _fake_agent_incomplete_frontier(*_args: Any, **_kwargs: Any) -> Mapping[str, Any]:
        return {
            "frontier_kind": "agent_incomplete",
            "not_proven": ["probe frontier only"],
            "proof_limits": ["support projection probe only"],
        }

    reporter.observe_building_frontier = _fake_agent_incomplete_frontier
    try:
        event_kind = reporter.building_event_kind_from_frontier(
            Path("agent-incomplete-frontier-probe"),
            repo_root=Path.cwd(),
        )
    finally:
        reporter.observe_building_frontier = original_observer
    if event_kind != "intervention_required":
        raise ProfileError(
            "reporter agent_incomplete frontier must emit intervention_required, "
            f"got {event_kind!r}"
        )
    owner = reporter._required_disposition_owner({"frontier_kind": "agent_incomplete"})
    if owner != "caller-or-coo":
        raise ProfileError(
            "reporter agent_incomplete frontier must project caller-or-coo owner, "
            f"got {owner!r}"
        )
    return 2


def _extract_js_const_object(source: str, const_name: str) -> Mapping[str, Any]:
    marker = f"export const {const_name} ="
    marker_index = source.find(marker)
    if marker_index < 0:
        raise ProfileError(f"labels.js missing export const {const_name}")
    start = source.find("{", marker_index)
    if start < 0:
        raise ProfileError(f"labels.js export const {const_name} has no object literal")
    depth = 0
    quote = ""
    escaped = False
    for index in range(start, len(source)):
        char = source[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                literal = source[start : index + 1]
                break
    else:
        raise ProfileError(f"labels.js export const {const_name} object did not close")
    literal = re.sub(r"//.*", "", literal)
    literal = re.sub(r"([,{]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r"\1'\2':", literal)
    try:
        parsed = ast.literal_eval(literal)
    except (SyntaxError, ValueError) as exc:
        raise ProfileError(f"labels.js export const {const_name} did not parse: {exc}") from exc
    if not isinstance(parsed, Mapping):
        raise ProfileError(f"labels.js export const {const_name} is not a mapping")
    return dict(parsed)


def _assert_reporter_message_shape(report_sinks: Any) -> tuple[str, int]:
    packet = {
        **_minimal_reporter_packet(),
        "report_id": "reporter-message-shape-probe",
        "building_id": "customer-language-probe",
        "human_title": "알림 말투 점검",
        "observed_board_state": "observed_closed_boundary",
        "trigger_event_ref": "building-event:building_finished:customer-language-probe",
        "current_brick_ref": "brick-work",
        "current_work_kind": "work",
        "current_lane": "worker",
        "last_completed_step_ref": "work/step-outputs/customer-language-probe-work-attempt-1/step-output.json",
        "frontier_ref": "project/brick-protocol/buildings/customer-language-probe#frontier:complete:event:building_finished",
        "sink_refs": ["report-sink:slack"],
    }
    finished_text = report_sinks._slack_message_text(packet)
    finished_top_level_text = report_sinks._slack_message_text(packet, force_top_level=True)
    intervention_packet = {
        **packet,
        "observed_board_state": "needs_disposition",
        "trigger_event_ref": "building-event:intervention_required:customer-language-probe",
        "frontier_ref": (
            "project/brick-protocol/buildings/customer-language-probe"
            "#frontier:human_review_waiting:event:intervention_required"
        ),
        "required_disposition_owner": "caller-or-coo",
    }
    intervention_text = report_sinks._slack_message_text(intervention_packet)
    intervention_top_level_text = report_sinks._slack_message_text(
        intervention_packet,
        force_top_level=True,
    )
    started_text = report_sinks._slack_message_text(
        {
            **packet,
            "trigger_event_ref": "building-event:building_started:customer-language-probe",
            "observed_board_state": "observed_started",
            "structure_diagram": "[작업·워커] ──▶ (완료)",
        }
    )
    text = "\n---\n".join(
        (
            started_text,
            finished_text,
            intervention_text,
            finished_top_level_text,
            intervention_top_level_text,
        )
    )
    required_fragments = (
        "알림 말투 점검",
        "시작했어요.",
        "진행되는 대로 여기 댓글로 알려드릴게요.",
        "```",
        "[작업·워커] ──▶ (완료)",
        "✅ 다 됐어요!",
        "잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)",
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise ProfileError(f"Slack message shape missing fragment {fragment!r}:\n{text}")
    if finished_text != "✅ 다 됐어요!":
        raise ProfileError(f"building_finished reply text was not clean:\n{finished_text}")
    if intervention_text != "잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)":
        raise ProfileError(f"intervention_required reply text was not clean:\n{intervention_text}")
    if not finished_top_level_text.startswith("🧱 알림 말투 점검\n"):
        raise ProfileError(
            f"building_finished fallback text was not top-level titled:\n{finished_top_level_text}"
        )
    if not intervention_top_level_text.startswith("🧱 알림 말투 점검\n"):
        raise ProfileError(
            "intervention_required fallback text was not top-level titled:\n"
            f"{intervention_top_level_text}"
        )
    forbidden_fragments = (
        "ref:",
        "brick=",
        "step=",
        "frontier=",
        "※",
        "누구:",
        "다음:",
    )
    for fragment in forbidden_fragments:
        if fragment in text:
            raise ProfileError(f"Slack message leaked customer-facing jargon {fragment!r}:\n{text}")
    forbidden_legacy_fragments = (
        "Brick:",
        "Agent:",
        "Link:",
        "work/step-outputs",
        "마지막 완료 step",
        "step=-",
        "brick=-",
        "운영 refs:",
    )
    for fragment in forbidden_legacy_fragments:
        if fragment in text:
            raise ProfileError(f"Slack message leaked legacy wording {fragment!r}:\n{text}")
    empty_probe = report_sinks._slack_message_text(
        {
            **packet,
            "report_id": "reporter-message-empty-field-probe",
            "current_brick_ref": "",
            "last_completed_step_ref": "",
            "frontier_ref": "project/brick-protocol/buildings/customer-language-probe#frontier:complete",
        }
    )
    for fragment in (*forbidden_fragments, "step=-", "brick=-"):
        if fragment in empty_probe:
            raise ProfileError(f"Slack empty-field probe leaked {fragment!r}:\n{empty_probe}")
    return text, len(required_fragments) + len(forbidden_fragments) + len(forbidden_legacy_fragments) + 1


# EXPLICIT NO-CREDS REPORT ENV (footgun-fix robustness). An EMPTY report_env
# ({}) now AUTO-LOADS ~/.brick/report.env at the run.py engine seam (so a caller
# passing {} can never silently close the Slack gate). That means a literal {}
# no longer reliably exercises the "no Slack creds -> env-gated sink drops"
# coverage on a developer machine that HAS report.env. To keep that coverage
# EXPLICIT (and decoupled from the vessel gate), the no-env probes thread this
# NON-EMPTY mapping that deliberately carries NO BRICK_REPORT_*/BRICK_DASHBOARD_*
# credential key: it is truthy (so it bypasses the empty==auto-load branch) yet
# leaves _slack_environment_ready/_dashboard_environment_ready False on purpose.
_NO_CREDS_REPORT_ENV: dict[str, str] = {"BRICK_REPORT_PROBE_NO_CREDS": "1"}


def _assert_reporter_auto_wiring(repo: Path, reporter: Any, report_sinks: Any) -> tuple[str, str, str, int]:
    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.brick.work import parse_required_return_shape
    from support.checkers.lib.case_runners import _preset_completion_command_runner

    inspected = 0
    command_runner = _preset_completion_command_runner(LocalCliCompleted)

    def _brain(request: Any) -> Mapping[str, Any]:
        returned: dict[str, Any] = {}
        for label in parse_required_return_shape(request.required_return_shape):
            if label == "made_changes":
                returned[label] = ["notification auto-wire probe change"]
            elif label == "observed_evidence":
                returned[label] = ["notification auto-wire probe evidence"]
            elif label == "not_proven":
                returned[label] = ["semantic correctness of notification probe work"]
            else:
                returned[label] = f"probe value for {label}"
        return returned

    with tempfile.TemporaryDirectory(prefix="bp-reporter-auto-wire-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        no_env_plan = _reporter_auto_wire_plan("reporter-auto-wire-no-env")
        with _without_report_grain_env():
            result = run_building_plan(
                no_env_plan,
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                command_runner=command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                # EXPLICIT no-creds env (not {}): {} now auto-loads, so an empty
                # dict would no longer prove the "no Slack env -> env-gated sink
                # drops" coverage on a machine WITH ~/.brick/report.env. This
                # truthy, credential-free mapping suppresses the env-gated sinks
                # ON PURPOSE and bypasses the empty==auto-load branch.
                report_env=_NO_CREDS_REPORT_ENV,
            )
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 5:
            raise ProfileError(
                "basic auto-wiring without Slack env should emit start, brick, and terminal observations"
            )
        for observation in observations:
            sink_refs = observation.get("report_packet", {}).get("sink_refs", [])
            if sink_refs != ["report-sink:local-inbox"]:
                raise ProfileError(
                    f"auto-wiring without Slack env attempted unexpected sinks: {sink_refs}"
                )
        inbox_packets = sorted((temp_repo / "project" / "brick-protocol" / "status" / "inbox").glob("*.json"))
        if len(inbox_packets) != 5:
            raise ProfileError("basic auto-wiring without Slack env did not write five local inbox packets")
        local_inbox_text = inbox_packets[0].read_text(encoding="utf-8")
        inspected += 4

    temp_sent_messages: list[str] = []

    def _fake_temp_slack_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
        del timeout_seconds
        payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
        temp_sent_messages.append(str(payload.get("text") or ""))
        return 200, b'{"ok":true}'

    with tempfile.TemporaryDirectory(prefix="bp-reporter-auto-wire-slack-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        repo_inbox = repo / "project" / "brick-protocol" / "status" / "inbox"
        repo_inbox_before = sorted(path.name for path in repo_inbox.glob("*.json")) if repo_inbox.is_dir() else []
        fake_env = {
            "BRICK_REPORT_SLACK_BOT_TOKEN": "xoxb-redacted-probe",
            "BRICK_REPORT_SLACK_CHANNEL_ID": "CREDPROBE",
        }
        with _without_report_grain_env():
            result = run_building_plan(
                _reporter_auto_wire_plan("reporter-auto-wire-fake-slack"),
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                command_runner=command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                report_env=fake_env,
                report_slack_sender=_fake_temp_slack_sender,
            )
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 5:
            raise ProfileError("temp-root auto-wiring with fake Slack env emitted wrong event count")
        for observation in observations:
            sink_refs = observation.get("report_packet", {}).get("sink_refs", [])
            if sink_refs != ["report-sink:local-inbox"]:
                raise ProfileError(f"temp-root auto-wiring used external sinks: {sink_refs}")
        if temp_sent_messages:
            raise ProfileError(f"temp-root fake Slack sender was invoked: {len(temp_sent_messages)}")
        repo_inbox_after = sorted(path.name for path in repo_inbox.glob("*.json")) if repo_inbox.is_dir() else []
        if repo_inbox_after != repo_inbox_before:
            raise ProfileError("temp-root auto-wiring touched the real repo inbox")
        inspected += 5

    real_sent_messages: list[str] = []

    def _fake_real_slack_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
        del timeout_seconds
        payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
        real_sent_messages.append(str(payload.get("text") or ""))
        return 200, b'{"ok":true}'

    with tempfile.TemporaryDirectory(prefix="bp-reporter-real-vessel-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        fake_env = {
            "BRICK_REPORT_SLACK_BOT_TOKEN": "xoxb-redacted-probe",
            "BRICK_REPORT_SLACK_CHANNEL_ID": "CREDPROBE",
        }
        original_reporter_root = reporter.REPO_ROOT
        try:
            reporter.REPO_ROOT = temp_repo
            result = run_building_plan(
                _reporter_auto_wire_plan(
                    "reporter-auto-wire-real-vessel",
                    report_event_policy={
                        "enabled": True,
                        "mode": "basic",
                        "grain": "building",
                        "event_kinds": ["building_finished"],
                        "sink_refs": ["report-sink:local-inbox", "report-sink:slack"],
                        "allow_real_slack_delivery": True,
                    },
                ),
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                command_runner=command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                report_env=fake_env,
                report_slack_sender=_fake_real_slack_sender,
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 1:
            raise ProfileError("real-vessel completion emitted wrong event count")
        sink_refs = observations[0].get("report_packet", {}).get("sink_refs", [])
        if sink_refs != ["report-sink:local-inbox", "report-sink:slack"]:
            raise ProfileError(f"real-vessel completion used wrong sinks: {sink_refs}")
        if len(real_sent_messages) != 1:
            raise ProfileError(
                f"real-vessel fake Slack sender count expected 1, observed {len(real_sent_messages)}"
            )
        inspected += 4

    verbose_text = ""
    with tempfile.TemporaryDirectory(prefix="bp-reporter-verbose-mode-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        result = run_building_plan(
            _reporter_auto_wire_plan(
                "reporter-verbose-mode",
                step_kinds=("design", "work"),
                report_event_policy={
                    "enabled": True,
                    "mode": "verbose",
                    "grain": "building",
                    "event_kinds": ["building_finished"],
                    "sink_refs": ["report-sink:local-inbox"],
                },
            ),
            output_root=output_root,
            overwrite_existing=True,
            local_callables={"callable:local:agent-invoke0-smoke": _brain},
            command_runner=command_runner,
            adapter_cwd=repo,
            adapter_timeout_seconds=10,
            # EXPLICIT no-creds env (not {}): keep this probe credential-free and
            # off the empty==auto-load path (the policy only declares local-inbox,
            # so Slack delivery never applies; this just avoids pulling real
            # ~/.brick/report.env creds into a render-only test).
            report_env=_NO_CREDS_REPORT_ENV,
        )
        observations = tuple(getattr(result, "_report_event_observations", ()))
        if len(observations) != 1:
            raise ProfileError("verbose-mode temp drive emitted wrong event count")
        packet = observations[0].get("report_packet", {})
        verbose_text = report_sinks._slack_message_text(packet)
        if "✅ 다 됐어요!" not in verbose_text:
            raise ProfileError(f"verbose-mode message did not render plain completion:\n{verbose_text}")
        for fragment in ("단계: ", "ref:", "누구:", "다음:"):
            if fragment in verbose_text:
                raise ProfileError(f"verbose-mode message leaked old Slack fragment {fragment!r}:\n{verbose_text}")
        inspected += 3

    return real_sent_messages[0], local_inbox_text, verbose_text, inspected


def _assert_reporter_brick_grain_threading(
    repo: Path,
    reporter: Any,
    report_sinks: Any,
) -> tuple[str, str, int]:
    from brick_protocol.support.connection.agent_adapter import LocalCliCompleted
    from brick_protocol.support.operator.run import run_building_plan
    from brick_protocol.brick.work import parse_required_return_shape
    from support.checkers.lib.case_runners import _preset_completion_command_runner

    inspected = 0
    command_runner = _preset_completion_command_runner(LocalCliCompleted)

    sent_payloads: list[Mapping[str, Any]] = []

    def _brain(request: Any) -> Mapping[str, Any]:
        thread_payloads_during_work = [payload for payload in sent_payloads if payload.get("thread_ts")]
        received_during_work = [
            payload
            for payload in thread_payloads_during_work
            if "시작했어요." in str(payload.get("text") or "")
            and "진행되는 대로" not in str(payload.get("text") or "")
        ]
        returned_or_gate_during_work = [
            payload
            for payload in thread_payloads_during_work
            if "단계 끝났어요" in str(payload.get("text") or "")
            or "마무리예요" in str(payload.get("text") or "")
        ]
        if len(received_during_work) != 1:
            raise ProfileError(
                "brick grain work-time probe expected brick_received before Agent work, "
                f"got {len(received_during_work)}"
            )
        if returned_or_gate_during_work:
            raise ProfileError(
                "brick grain work-time probe observed brick_returned/gate_passed before Agent work"
            )
        returned: dict[str, Any] = {}
        for label in parse_required_return_shape(request.required_return_shape):
            if label == "made_changes":
                returned[label] = ["brick grain probe change"]
            elif label == "observed_evidence":
                returned[label] = ["brick grain probe evidence"]
            elif label == "not_proven":
                returned[label] = ["semantic correctness of brick grain probe work"]
            else:
                returned[label] = f"probe value for {label}"
        return returned

    building_policy = reporter.report_event_policy_from_plan(
        {
            "report_event_policy": {
                "enabled": True,
                "grain": "building",
            }
        }
    )
    if building_policy.get("event_kinds") != [
        "building_started",
        "intervention_required",
        "building_finished",
    ]:
        raise ProfileError("building grain policy did not preserve the three existing event kinds")
    default_policy = reporter.report_event_policy_from_plan({})
    brick_policy = reporter.report_event_policy_from_plan(
        {
            "report_event_policy": {
                "enabled": True,
                "grain": "brick",
            }
        }
    )
    expected_brick_events = [
        "building_started",
        "intervention_required",
        "building_finished",
        "brick_received",
        "brick_returned",
        "gate_passed",
        "disposition_applied",
    ]
    if brick_policy.get("event_kinds") != expected_brick_events:
        raise ProfileError(
            "brick grain policy did not extend event kinds additively: "
            f"{brick_policy.get('event_kinds')!r}"
        )
    if (
        default_policy.get("event_kinds") != expected_brick_events
        or default_policy.get("report_event_grain") != "brick"
    ):
        raise ProfileError(
            "absent report policy did not default to brick grain: "
            f"{default_policy!r}"
        )
    inspected += 6

    def _fake_thread_slack_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
        del timeout_seconds
        payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
        sent_payloads.append(payload)
        if payload.get("thread_ts"):
            return 200, b'{"ok":true}'
        return 200, b'{"ok":true,"ts":"1718200000.000100","channel":"CREDPROBE"}'

    fake_env = {
        "BRICK_REPORT_SLACK_BOT_TOKEN": "xoxb-redacted-probe",
        "BRICK_REPORT_SLACK_CHANNEL_ID": "CREDPROBE",
    }
    brick_reply_text = ""
    received_reply_text = ""
    gate_reply_text = ""
    nonterminal_gate_text = ""
    disposition_reply_text = ""
    intervention_reply_text = ""
    finished_reply_text = ""
    fallback_intervention_text = ""
    fallback_finished_text = ""
    with tempfile.TemporaryDirectory(prefix="bp-reporter-brick-grain-") as tmpdir:
        temp_repo = Path(tmpdir)
        _copy_reporter_probe_agent_resources(repo, temp_repo)
        output_root = temp_repo / "project" / "brick-protocol" / "buildings"
        original_reporter_root = reporter.REPO_ROOT
        try:
            reporter.REPO_ROOT = temp_repo
            result = run_building_plan(
                _reporter_auto_wire_plan("reporter-brick-grain-thread"),
                output_root=output_root,
                overwrite_existing=True,
                local_callables={"callable:local:agent-invoke0-smoke": _brain},
                command_runner=command_runner,
                adapter_cwd=repo,
                adapter_timeout_seconds=10,
                report_env=fake_env,
                report_slack_sender=_fake_thread_slack_sender,
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root

        root = output_root / "reporter-brick-grain-thread"
        thread_path = root / "raw" / "report-thread.jsonl"
        if not thread_path.is_file():
            raise ProfileError("brick grain parent Slack ts was not recorded in raw/report-thread.jsonl")
        thread_text = thread_path.read_text(encoding="utf-8")
        if "1718200000.000100" not in thread_text or "CREDPROBE" not in thread_text:
            raise ProfileError("brick grain thread record did not preserve ts + channel ref")

        observations = tuple(getattr(result, "_report_event_observations", ()))
        trigger_refs = [
            str(observation.get("report_packet", {}).get("trigger_event_ref") or "")
            for observation in observations
            if isinstance(observation, Mapping)
        ]
        for event_kind in ("brick_received", "brick_returned", "gate_passed"):
            if not any(event_kind in trigger for trigger in trigger_refs):
                raise ProfileError(f"brick grain did not emit {event_kind} support event")
        delivery_path = root / "raw" / "report-delivery.jsonl"
        if not delivery_path.is_file():
            raise ProfileError("brick grain delivery timing was not recorded in raw/report-delivery.jsonl")
        delivery_records: list[Mapping[str, Any]] = []
        for line in delivery_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProfileError("raw/report-delivery.jsonl contained invalid JSON") from exc
            if not isinstance(record, Mapping):
                raise ProfileError("raw/report-delivery.jsonl contained a non-mapping record")
            if record.get("kind") == "report_delivery_observation":
                delivery_records.append(record)
        if not delivery_records:
            raise ProfileError("raw/report-delivery.jsonl contained no report delivery observations")

        def _delivery_timestamp(record: Mapping[str, Any]) -> datetime:
            delivered_at = str(record.get("delivered_at") or "").strip()
            if not delivered_at:
                raise ProfileError(f"report delivery record missing delivered_at: {record!r}")
            try:
                return datetime.fromisoformat(delivered_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ProfileError(
                    f"report delivery record delivered_at is not ISO datetime: {delivered_at!r}"
                ) from exc

        active_sink_refs = {
            str(record.get("sink_ref") or "")
            for record in delivery_records
            if str(record.get("event_kind") or "") == "brick_received"
        }
        active_sink_refs.discard("")
        if active_sink_refs != {"report-sink:local-inbox", "report-sink:slack"}:
            raise ProfileError(
                "brick grain expected local-inbox and Slack brick_received delivery records, "
                f"got {sorted(active_sink_refs)!r}"
            )
        by_event_and_sink: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
        for record in delivery_records:
            if record.get("source_truth") is not False:
                raise ProfileError("report delivery record source_truth is not false")
            key = (
                str(record.get("event_kind") or ""),
                str(record.get("sink_ref") or ""),
            )
            by_event_and_sink.setdefault(key, []).append(record)
        for sink_ref in sorted(active_sink_refs):
            received_records = by_event_and_sink.get(("brick_received", sink_ref), [])
            if len(received_records) != 1:
                raise ProfileError(
                    f"brick grain expected one brick_received delivery record for {sink_ref}, "
                    f"got {len(received_records)}"
                )
            received_at = _delivery_timestamp(received_records[0])
            for later_event in ("brick_returned", "gate_passed", "building_finished"):
                later_records = by_event_and_sink.get((later_event, sink_ref), [])
                if len(later_records) != 1:
                    raise ProfileError(
                        f"brick grain expected one {later_event} delivery record for {sink_ref}, "
                        f"got {len(later_records)}"
                    )
                later_at = _delivery_timestamp(later_records[0])
                if not received_at < later_at:
                    raise ProfileError(
                        "brick_received delivery was not earlier than completion delivery "
                        f"for {sink_ref}/{later_event}: {received_at.isoformat()} >= "
                        f"{later_at.isoformat()}"
                    )

        thread_payloads = [payload for payload in sent_payloads if payload.get("thread_ts")]
        if len(thread_payloads) != 4:
            raise ProfileError(
                "brick grain expected brick_received, brick_returned, gate_passed, "
                f"and completion Slack thread replies, got {len(thread_payloads)}"
            )
        for payload in thread_payloads:
            if payload.get("thread_ts") != "1718200000.000100":
                raise ProfileError(f"brick grain reply carried wrong thread_ts: {payload!r}")
        received_payloads = [
            payload
            for payload in thread_payloads
            if "시작했어요." in str(payload.get("text") or "")
            and "진행되는 대로" not in str(payload.get("text") or "")
        ]
        returned_payloads = [
            payload
            for payload in thread_payloads
            if "단계 끝났어요" in str(payload.get("text") or "")
        ]
        gate_payloads = [
            payload
            for payload in thread_payloads
            if "마무리예요" in str(payload.get("text") or "")
        ]
        if len(received_payloads) != 1:
            raise ProfileError(
                "brick grain expected exactly one brick_received Slack thread reply, "
                f"got {len(received_payloads)}"
            )
        if len(returned_payloads) != 1:
            raise ProfileError(
                "brick grain expected exactly one brick_returned Slack thread reply, "
                f"got {len(returned_payloads)}"
            )
        if len(gate_payloads) != 1:
            raise ProfileError(
                "brick grain expected exactly one terminal gate_passed Slack thread reply, "
                f"got {len(gate_payloads)}"
            )
        received_reply_text = str(received_payloads[0].get("text") or "")
        brick_reply_text = str(returned_payloads[0].get("text") or "")
        gate_reply_text = str(gate_payloads[0].get("text") or "")
        for fragment in ("①", "작업", "시작했어요.", "담당: Codex Local", "("):
            if fragment not in received_reply_text:
                raise ProfileError(
                    f"brick_received Slack reply missing fragment {fragment!r}:\n{received_reply_text}"
                )
        for fragment in ("①", "작업", "단계 끝났어요", "담당: Codex Local", "("):
            if fragment not in brick_reply_text:
                raise ProfileError(
                    f"brick grain Slack reply missing fragment {fragment!r}:\n{brick_reply_text}"
                )
        for fragment in ("①", "작업", "확인했어요.", "마무리예요", "("):
            if fragment not in gate_reply_text:
                raise ProfileError(
                    f"gate_passed Slack reply missing fragment {fragment!r}:\n{gate_reply_text}"
                )
        for label, reply_text in (
            ("brick_received", received_reply_text),
            ("brick_returned", brick_reply_text),
            ("gate_passed", gate_reply_text),
        ):
            if not re.search(r"\(\d{2}:\d{2}\)", reply_text):
                raise ProfileError(
                    f"{label} Slack reply did not render KST HH:MM times:\n{reply_text}"
                )
            for fragment in ("ref:", "brick=", "frontier=", "※", "누구:", "다음:"):
                if fragment in reply_text:
                    raise ProfileError(
                        f"{label} Slack reply leaked forbidden fragment {fragment!r}:\n{reply_text}"
                    )
        nonterminal_gate_text = report_sinks._slack_message_text(
            {
                **_minimal_reporter_packet(),
                "report_id": "reporter-gate-nonterminal-probe",
                "building_id": "reporter-brick-grain-thread",
                "trigger_event_ref": "building-event:gate_passed:reporter-brick-grain-thread",
                "current_work_kind": "work",
                "current_lane": "worker",
                "event_context": {
                    "sequence_index": 1,
                    "returned_at": "2026-06-12T00:01:00+00:00",
                    "next_brick_instance_ref": "brick-review",
                    "next_work_kind": "review",
                },
            }
        )
        for fragment in ("①", "작업", "다음 단계(검수)", "넘어가요", "(09:01)"):
            if fragment not in nonterminal_gate_text:
                raise ProfileError(
                    f"nonterminal gate_passed Slack reply missing fragment {fragment!r}:\n"
                    f"{nonterminal_gate_text}"
                )
        finished_payloads = [
            payload
            for payload in thread_payloads
            if "✅ 다 됐어요!" in str(payload.get("text") or "")
        ]
        if len(finished_payloads) != 1:
            raise ProfileError(
                "brick grain expected one completion Slack thread reply, "
                f"got {len(finished_payloads)}"
            )
        finished_reply_text = str(finished_payloads[0].get("text") or "")
        if finished_reply_text != "✅ 다 됐어요!":
            raise ProfileError(
                f"building_finished Slack reply was not a clean comment:\n{finished_reply_text}"
            )
        if "🧱" in finished_reply_text:
            raise ProfileError(
                f"building_finished Slack reply leaked parent title marker:\n{finished_reply_text}"
            )
        inspected += 21

        intervention_payloads: list[Mapping[str, Any]] = []

        def _fake_intervention_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
            intervention_payloads.append(payload)
            return 200, b'{"ok":true}'

        original_reporter_root = reporter.REPO_ROOT
        reporter.REPO_ROOT = temp_repo
        try:
            intervention_packet = reporter.render_building_event_report_packet(
                event_kind="intervention_required",
                building_id="reporter-brick-grain-thread",
                building_root=root,
                current_brick_ref="brick-work",
                last_completed_step_ref="work/step-outputs/reporter-brick-grain-thread-work-attempt-1/step-output.json",
                required_disposition_owner="caller-or-coo",
                sink_refs=["report-sink:slack"],
                repo_root=temp_repo,
                generated_at="2026-06-12T00:03:00+00:00",
                report_event_grain="brick",
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        intervention_observation = report_sinks.send_slack_report_packet(
            intervention_packet,
            repo_root=temp_repo,
            allow_real_delivery=True,
            env=fake_env,
            sender=_fake_intervention_sender,
        )
        if intervention_observation.delivered is not True or len(intervention_payloads) != 1:
            raise ProfileError("intervention_required probe did not send exactly one thread reply")
        if intervention_payloads[0].get("thread_ts") != "1718200000.000100":
            raise ProfileError("intervention_required reply did not carry recorded thread_ts")
        intervention_reply_text = str(intervention_payloads[0].get("text") or "")
        if intervention_reply_text != "잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)":
            raise ProfileError(
                "intervention_required Slack reply was not a clean owner-labeled comment:\n"
                f"{intervention_reply_text}"
            )
        if "🧱" in intervention_reply_text:
            raise ProfileError(
                f"intervention_required Slack reply leaked parent title marker:\n{intervention_reply_text}"
            )
        inspected += 4

        missing_thread_payloads: list[Mapping[str, Any]] = []
        fallback_payloads: list[Mapping[str, Any]] = []

        def _should_not_send(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            missing_thread_payloads.append(json.loads(bytes(request.data or b"{}").decode("utf-8")))
            return 200, b'{"ok":true}'

        def _fallback_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            fallback_payloads.append(json.loads(bytes(request.data or b"{}").decode("utf-8")))
            return 200, b'{"ok":true}'

        original_reporter_root = reporter.REPO_ROOT
        reporter.REPO_ROOT = temp_repo
        missing_thread_root = output_root / "missing-thread-case"
        missing_thread_root.mkdir(parents=True)
        # SLACK VESSEL-GATE narrowing (slack-wiring-gap 0619): the vessel
        # predicate now requires a REAL declared-building-plan spine (not just the
        # project/<id>/buildings path shape) before external Slack delivery is
        # allowed. This synthetic root models a genuine building that simply has
        # NOT recorded a Slack thread parent yet -- so it must carry a real spine,
        # otherwise external_delivery_allowed would be stripped by the vessel gate
        # and the missing-thread / fallback probes below would observe
        # not_attempted_non_real_vessel instead of the thread-status classes they
        # are pinning.
        (missing_thread_root / "declared-building-plan.json").write_text(
            json.dumps(
                {
                    "brick_steps": [
                        {
                            "completion_edge_ref": "edge:missing-thread-design-to-work",
                            "rows": [
                                {
                                    "axis": "Brick",
                                    "brick_instance_ref": "brick-missing-thread-design",
                                    "brick_work_ref": "work:missing-thread-design",
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        try:
            missing_observations = []
            for event_kind in ("brick_received", "brick_returned", "gate_passed"):
                missing_packet = reporter.render_building_event_report_packet(
                    event_kind=event_kind,
                    building_id="missing-thread-case",
                    building_root=missing_thread_root,
                    current_brick_ref="brick-work",
                    last_completed_step_ref="work/step-outputs/missing-thread-case-work-attempt-1/step-output.json",
                    sink_refs=["report-sink:slack"],
                    repo_root=temp_repo,
                    generated_at="2026-06-12T00:00:00+00:00",
                    event_context={
                        "step_ref": "missing-thread-case-work",
                        "sequence_index": 1,
                        "received_at": "2026-06-12T00:00:00+00:00",
                        "returned_at": "2026-06-12T00:01:00+00:00",
                        "gate_note": "통과→다음스텝",
                        "next_brick_instance_ref": "brick-review",
                        "next_work_kind": "review",
                    },
                )
                missing_observations.append(
                    report_sinks.send_slack_report_packet(
                        missing_packet,
                        repo_root=temp_repo,
                        allow_real_delivery=True,
                        env=fake_env,
                        sender=_should_not_send,
                    )
                )
            fallback_observations = []
            for event_kind in ("intervention_required", "building_finished"):
                fallback_packet = reporter.render_building_event_report_packet(
                    event_kind=event_kind,
                    building_id="missing-thread-case",
                    building_root=missing_thread_root,
                    current_brick_ref="brick-work",
                    last_completed_step_ref=(
                        "work/step-outputs/missing-thread-case-work-attempt-1/"
                        "step-output.json"
                    ),
                    required_disposition_owner="caller-or-coo",
                    sink_refs=["report-sink:slack"],
                    repo_root=temp_repo,
                    generated_at="2026-06-12T00:04:00+00:00",
                    report_event_grain="brick",
                )
                fallback_observations.append(
                    report_sinks.send_slack_report_packet(
                        fallback_packet,
                        repo_root=temp_repo,
                        allow_real_delivery=True,
                        env=fake_env,
                        sender=_fallback_sender,
                    )
                )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        if any(
            observation.delivery_status_class != "not_attempted_missing_thread_ts"
            for observation in missing_observations
        ):
            raise ProfileError("brick grain missing-thread Slack sends did not all fail closed")
        if missing_thread_payloads:
            raise ProfileError("brick grain missing-thread probe still called Slack sender")
        if any(observation.delivered is not True for observation in fallback_observations):
            raise ProfileError("HOLD/FINISH missing-thread fallback did not send")
        if len(fallback_payloads) != 2:
            raise ProfileError(
                f"HOLD/FINISH missing-thread fallback sent {len(fallback_payloads)} payload(s)"
            )
        for payload in fallback_payloads:
            if payload.get("thread_ts"):
                raise ProfileError(f"missing-thread fallback unexpectedly carried thread_ts: {payload!r}")
        fallback_intervention_text = str(fallback_payloads[0].get("text") or "")
        fallback_finished_text = str(fallback_payloads[1].get("text") or "")
        if fallback_intervention_text != (
            "🧱 missing-thread-case\n"
            "잠깐 멈췄어요. 살펴봐 주세요. (담당: 호출자 또는 COO)"
        ):
            raise ProfileError(
                "intervention_required missing-thread fallback did not preserve titled form:\n"
                f"{fallback_intervention_text}"
            )
        if fallback_finished_text != "🧱 missing-thread-case\n✅ 다 됐어요!":
            raise ProfileError(
                "building_finished missing-thread fallback did not preserve titled form:\n"
                f"{fallback_finished_text}"
            )
        inspected += 5

        disposition_payloads: list[Mapping[str, Any]] = []

        def _fake_disposition_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            payload = json.loads(bytes(request.data or b"{}").decode("utf-8"))
            disposition_payloads.append(payload)
            return 200, b'{"ok":true}'

        original_reporter_root = reporter.REPO_ROOT
        reporter.REPO_ROOT = temp_repo
        try:
            disposition_packet = reporter.render_building_event_report_packet(
                event_kind="disposition_applied",
                building_id="reporter-brick-grain-thread",
                building_root=root,
                current_brick_ref="brick-work",
                last_completed_step_ref="work/step-outputs/reporter-brick-grain-thread-work-attempt-1/step-output.json",
                sink_refs=["report-sink:slack"],
                repo_root=temp_repo,
                generated_at="2026-06-12T00:02:00+00:00",
                event_context={
                    "disposition_action": "forward",
                    "disposition_author_ref": "coo:checker",
                    "applied_at": "2026-06-12T00:02:00+00:00",
                },
            )
        finally:
            reporter.REPO_ROOT = original_reporter_root
        disposition_observation = report_sinks.send_slack_report_packet(
            disposition_packet,
            repo_root=temp_repo,
            allow_real_delivery=True,
            env=fake_env,
            sender=_fake_disposition_sender,
        )
        if disposition_observation.delivered is not True or len(disposition_payloads) != 1:
            raise ProfileError("disposition_applied probe did not send exactly one thread reply")
        if disposition_payloads[0].get("thread_ts") != "1718200000.000100":
            raise ProfileError("disposition_applied reply did not carry recorded thread_ts")
        disposition_reply_text = str(disposition_payloads[0].get("text") or "")
        if "⤷ COO 확인" not in disposition_reply_text:
            raise ProfileError(
                f"disposition_applied reply did not render coo stamp:\n{disposition_reply_text}"
            )
        if "다음 단계로 진행" not in disposition_reply_text:
            raise ProfileError(
                "explicit-forward disposition_applied reply did not preserve the forward label:\n"
                f"{disposition_reply_text}"
            )
        missing_action_disposition_text = report_sinks._slack_message_text(
            {
                **_minimal_reporter_packet(),
                "report_id": "reporter-disposition-missing-action-probe",
                "building_id": "reporter-brick-grain-thread",
                "trigger_event_ref": (
                    "building-event:disposition_applied:reporter-brick-grain-thread"
                ),
                "current_work_kind": "work",
                "current_lane": "worker",
                "generated_at": "2026-06-12T00:02:00+00:00",
                "event_context": {
                    "disposition_author_ref": "coo:checker",
                    "applied_at": "2026-06-12T00:02:00+00:00",
                },
            }
        )
        for fragment in ("forward", "다음 단계로 진행"):
            if fragment in missing_action_disposition_text:
                raise ProfileError(
                    "missing-action disposition_applied reply rendered Movement-shaped "
                    f"default {fragment!r}:\n{missing_action_disposition_text}"
                )
        inspected += 5

        temp_root_payloads: list[Mapping[str, Any]] = []

        def _temp_root_sender(request: Any, timeout_seconds: float) -> tuple[int, bytes]:
            del timeout_seconds
            temp_root_payloads.append(json.loads(bytes(request.data or b"{}").decode("utf-8")))
            return 200, b'{"ok":true,"ts":"1718200000.000200","channel":"CREDPROBE"}'

        non_vessel_root = Path(tmpdir) / "non-vessel-building-root"
        non_vessel_root.mkdir()
        temp_root_policy = reporter.report_event_policy_from_plan(
            {
                "report_event_policy": {
                    "enabled": True,
                    "grain": "brick",
                    "sink_refs": ["report-sink:slack"],
                    "allow_real_slack_delivery": True,
                }
            }
        )
        for event_kind in (
            "brick_received",
            "brick_returned",
            "gate_passed",
            "disposition_applied",
        ):
            observation = reporter.emit_building_event_for_policy(
                temp_root_policy,
                event_kind=event_kind,
                building_id=f"temp-root-{event_kind}",
                building_root=non_vessel_root,
                current_brick_ref="brick-work",
                last_completed_step_ref=f"work/step-outputs/temp-root-{event_kind}/step-output.json",
                repo_root=temp_repo,
                slack_env=fake_env,
                slack_sender=_temp_root_sender,
                event_context={"sequence_index": 1},
            )
            if observation is not None:
                raise ProfileError(
                    f"brick grain F12 vessel guard leaked external sink for {event_kind}"
                )
        if temp_root_payloads:
            raise ProfileError(
                "brick grain F12 vessel guard invoked Slack sender for temp-root building"
            )
        inspected += 4

    return (
        "\n".join(
            text
            for text in (
                received_reply_text,
                brick_reply_text,
                gate_reply_text,
                nonterminal_gate_text,
                intervention_reply_text,
                finished_reply_text,
                fallback_intervention_text,
                fallback_finished_text,
            )
            if text
        ),
        disposition_reply_text,
        inspected,
    )


def _copy_reporter_probe_agent_resources(repo: Path, temp_repo: Path) -> None:
    source = repo / "agent"
    target = temp_repo / "agent"
    shutil.copytree(source, target)


def _reporter_auto_wire_plan(
    building_id: str,
    *,
    step_kinds: Sequence[str] = ("work",),
    report_event_policy: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    from support.checkers.lib.case_runners import _graph_test_plan_from_linear

    steps: list[Mapping[str, Any]] = []
    for index, kind in enumerate(step_kinds):
        step_ref = f"{building_id}-{kind}"
        brick_instance_ref = f"brick-{kind}"
        next_target = (
            f"brick-{step_kinds[index + 1]}"
            if index + 1 < len(step_kinds)
            else f"building-boundary:{building_id}-closed"
        )
        step: dict[str, Any] = {
            "step_ref": step_ref,
            "step_template_ref": f"building-step-template:{kind}",
        }
        step["rows"] = [
            {
                "axis": "Brick",
                "row_ref": f"brick-row:{step_ref}",
                "brick_work_ref": f"work:{step_ref}",
                "brick_instance_ref": brick_instance_ref,
                "work_statement": "Exercise reporter auto-wire notification projection.",
                "comparison_rule": "Support observes notification projection only.",
                "required_return_shape": "made_changes, observed_evidence, not_proven",
            },
            {
                "axis": "Agent",
                "row_ref": f"agent-row:{step_ref}",
                "agent_object_ref": {
                    "design": "agent-object:design-lead",
                    "work": "agent-object:dev",
                }.get(kind, "agent-object:dev"),
            },
            {
                "axis": "Link",
                "row_ref": f"link-row:{step_ref}",
                "movement": "forward",
                "target_ref": next_target,
                "declared_gate_refs": ["link-gate:default-transition"],
                "building_lifecycle": {
                    "state": "closed",
                    "reason": "reporter auto-wire probe closed boundary",
                },
            },
        ]
        steps.append(step)
    plan: dict[str, Any] = {
        "plan_ref": f"building-plan:{building_id}",
        "owner_axis": "Brick",
        "building_id": building_id,
        "plan_shape": "linear",
        "selected_adapter_ref": "adapter:codex-local",
        "task_source_ref": "task-source:inline-statement",
        "task_statement": f"# {building_id}\n\nExercise reporter auto-wire notification projection.",
        "steps": steps,
    }
    if report_event_policy is not None:
        plan["report_event_policy"] = dict(report_event_policy)
    return _graph_test_plan_from_linear(plan)


def _assert_no_scheduler_constructs(repo: Path) -> int:
    inspected = 0
    files = (
        repo / "support" / "operator" / "reporter.py",
        repo / "support" / "operator" / "report_sinks.py",
        repo / "support" / "operator" / "run.py",
        repo / "support" / "operator" / "walker_kernel.py",
    )
    forbidden_imports = {"threading", "sched", "queue", "asyncio"}
    forbidden_name_calls = {"sleep", "Thread", "Timer", "Queue"}
    forbidden_attr_calls = {
        ("time", "sleep"),
        ("threading", "Thread"),
        ("threading", "Timer"),
        ("queue", "Queue"),
        ("asyncio", "create_task"),
    }
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".", 1)[0] in forbidden_imports:
                        raise ProfileError(f"no-scheduler pin rejected import {alias.name} in {path}")
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".", 1)[0]
                if module in forbidden_imports:
                    raise ProfileError(f"no-scheduler pin rejected import from {node.module} in {path}")
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in forbidden_name_calls:
                    raise ProfileError(f"no-scheduler pin rejected call {func.id} in {path}")
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    if (func.value.id, func.attr) in forbidden_attr_calls:
                        raise ProfileError(
                            f"no-scheduler pin rejected call {func.value.id}.{func.attr} in {path}"
                        )
        inspected += 1
    return inspected


def _assert_reporter_dashboard_project_ref_guard(report_sinks: Any) -> str:
    calls: list[tuple[str, str | None]] = []
    original = report_sinks.send_dashboard_building_delta

    def fake_delta_sender(
        building_id: str,
        *,
        project_ref: str | None = None,
        **_: Any,
    ) -> Any:
        calls.append((building_id, project_ref))
        return report_sinks.ReportSinkObservation(
            sink_ref=report_sinks.DASHBOARD_SINK_REF,
            delivered=True,
            packet_ref=building_id,
            written_path="",
            proof_limits=("dashboard project_ref probe support evidence only",),
            not_proven=("real dashboard delivery",),
            delivery_status_class="http_2xx",
            provider_response_status_class="http_2xx",
        )

    base_packet = {
        **_minimal_reporter_packet(),
        "report_id": "reporter-dashboard-project-ref-probe",
        "building_id": "probe-building",
        "external_delivery_allowed": True,
        "sink_refs": [report_sinks.DASHBOARD_SINK_REF],
    }
    try:
        report_sinks.send_dashboard_building_delta = fake_delta_sender
        with tempfile.TemporaryDirectory(prefix="bp-dashboard-project-ref-probe-") as tmp:
            missing_observations = report_sinks.deliver_report_packet(
                base_packet,
                repo_root=Path(tmp),
                allow_real_dashboard_delivery=True,
            )
        if calls:
            raise ProfileError(
                "dashboard project_ref guard mutation-RED failed: missing project_ref "
                "still called send_dashboard_building_delta"
            )
        if len(missing_observations) != 1:
            raise ProfileError("dashboard project_ref guard did not return one observation")
        missing = missing_observations[0]
        if missing.delivered is not False:
            raise ProfileError("dashboard project_ref guard marked missing-project-ref delivered")
        if missing.delivery_status_class != "not_attempted_missing_project_ref":
            raise ProfileError(
                "dashboard project_ref guard returned wrong status class: "
                f"{missing.delivery_status_class!r}"
            )

        with tempfile.TemporaryDirectory(prefix="bp-dashboard-project-ref-probe-") as tmp:
            present_observations = report_sinks.deliver_report_packet(
                {**base_packet, "project_ref": "project:brick-protocol"},
                repo_root=Path(tmp),
                allow_real_dashboard_delivery=True,
            )
        if calls != [("probe-building", "project:brick-protocol")]:
            raise ProfileError(
                "dashboard project_ref guard did not pass packet project_ref into delta delivery"
            )
        if len(present_observations) != 1 or present_observations[0].delivered is not True:
            raise ProfileError("dashboard project_ref positive probe did not return delivered observation")
    finally:
        report_sinks.send_dashboard_building_delta = original
    return "dashboard project_ref guard observed: missing project_ref records non-delivery; present project_ref reaches delta sender; mutation-RED would call the sender on missing project_ref."


def _assert_reporter_structure_diagram_branch_rendering(reporter: Any) -> str:
    order = ["plan", "design-a", "design-b", "join", "work-a", "work-b", "done"]
    labels = {
        "plan": "[계획·PM]",
        "design-a": "[긴 설계 형제 A·Design]",
        "design-b": "[긴 설계 형제 B·Design]",
        "join": "[취합·PM]",
        "work-a": "[구현 형제 A·Dev]",
        "work-b": "[구현 형제 B·Dev]",
        "done": "[검수·QA]",
    }
    adjacency = {
        "plan": ["design-a", "design-b"],
        "design-a": ["join"],
        "design-b": ["join"],
        "join": ["work-a", "work-b"],
        "work-a": ["done"],
        "work-b": ["done"],
    }
    reverse = {
        "design-a": ["plan"],
        "design-b": ["plan"],
        "join": ["design-a", "design-b"],
        "work-a": ["join"],
        "work-b": ["join"],
        "done": ["work-a", "work-b"],
    }
    expected = "\n".join(
        [
            "[계획·PM]",
            "  │",
            "  ├─ [긴 설계 형제 A·Design]",
            "  └─ [긴 설계 형제 B·Design]",
            "  │",
            "[취합·PM]",
            "  │",
            "  ├─ [구현 형제 A·Dev]",
            "  └─ [구현 형제 B·Dev]",
            "  │",
            "[검수·QA]",
            "  │",
            "(완료)",
        ]
    )
    rendered = reporter._layered_structure_diagram(  # noqa: SLF001
        order,
        labels,
        adjacency=adjacency,
        reverse=reverse,
        terminal_sources={"done"},
    )
    if rendered != expected:
        raise ProfileError(
            "layered fan structure diagram changed unexpectedly:\n"
            f"expected:\n{expected}\nactual:\n{rendered}"
        )
    branch_lines = reporter._branch_structure_lines(  # noqa: SLF001
        ("[긴 설계 형제 A·Design]", "[긴 설계 형제 B·Design]"),
        prefix="  ",
    )
    mutated = "\n".join(
        line.replace("  └─", "    └─", 1) for line in branch_lines
    )
    if "\n".join(branch_lines) == mutated:
        raise ProfileError("structure diagram mutation-RED fixture did not alter branch indentation")
    if mutated in rendered:
        raise ProfileError(
            "structure diagram mutation-RED failed: accumulated branch indentation was accepted"
        )
    return "structure diagram branch rendering observed: layered fan siblings keep exact two-space branch prefix and mutation-RED indentation is absent."


def run_reporter_notification_projection(repo: Path) -> KernelResult:
    _ensure_import_identity(repo)
    reporter = importlib.import_module("brick_protocol.support.operator.reporter")
    report_sinks = importlib.import_module("brick_protocol.support.operator.report_sinks")
    label_parity_count = _assert_reporter_label_parity(repo)
    agent_incomplete_event_count = _assert_reporter_agent_incomplete_event_mapping(reporter)
    message_text, message_shape_count = _assert_reporter_message_shape(report_sinks)
    (
        auto_wire_message,
        auto_wire_inbox_text,
        verbose_mode_text,
        auto_wire_count,
    ) = _assert_reporter_auto_wiring(repo, reporter, report_sinks)
    (
        brick_grain_text,
        disposition_text,
        brick_grain_count,
    ) = _assert_reporter_brick_grain_threading(repo, reporter, report_sinks)
    no_scheduler_count = _assert_no_scheduler_constructs(repo)
    dashboard_project_ref_text = _assert_reporter_dashboard_project_ref_guard(report_sinks)
    structure_diagram_text = _assert_reporter_structure_diagram_branch_rendering(reporter)

    observations = tuple(reporter.reporter_negative_probe_observations())
    if not observations:
        raise ProfileError("reporter negative probes did not return observations")
    not_rejected = [
        str(observation.get("probe_ref") or "<missing-probe-ref>")
        for observation in observations
        if observation.get("rejected") is not True
    ]
    if not_rejected:
        raise ProfileError(
            "reporter negative probe(s) were not rejected: " + ", ".join(not_rejected)
        )
    owner_observations = tuple(reporter.reporter_owner_vocabulary_probe_observations())
    if not owner_observations:
        raise ProfileError("reporter owner vocabulary probes did not return observations")
    owner_not_passed = [
        str(observation.get("probe_ref") or "<missing-probe-ref>")
        for observation in owner_observations
        if observation.get("passed") is not True
    ]
    if owner_not_passed:
        raise ProfileError(
            "reporter owner vocabulary probe(s) did not pass: "
            + ", ".join(owner_not_passed)
        )
    delivery_wake_observations = tuple(reporter.reporter_delivery_wake_probe_observations())
    if not delivery_wake_observations:
        raise ProfileError("reporter delivery wake probes did not return observations")
    delivery_wake_not_passed = [
        str(observation.get("probe_ref") or "<missing-probe-ref>")
        for observation in delivery_wake_observations
        if observation.get("passed") is not True
    ]
    if delivery_wake_not_passed:
        raise ProfileError(
            "reporter delivery wake probe(s) did not pass: "
            + ", ".join(delivery_wake_not_passed)
        )
    event_hook_observations = tuple(reporter.reporter_event_hook_probe_observations())
    if not event_hook_observations:
        raise ProfileError("reporter event hook probes did not return observations")
    event_hook_not_passed = [
        str(observation.get("probe_ref") or "<missing-probe-ref>")
        for observation in event_hook_observations
        if observation.get("passed") is not True
    ]
    if event_hook_not_passed:
        raise ProfileError(
            "reporter event hook probe(s) did not pass: "
            + ", ".join(event_hook_not_passed)
        )

    packet = _minimal_reporter_packet()
    reporter.validate_report_packet(packet)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_repo = Path(tmp)
        sink_observations = report_sinks.deliver_report_packet(
            packet,
            repo_root=tmp_repo,
            overwrite_existing=False,
        )
        if len(sink_observations) != 1:
            raise ProfileError("local inbox sink did not return exactly one observation")
        sink_observation = sink_observations[0]
        if sink_observation.delivered is not True:
            raise ProfileError("local inbox sink observation did not mark delivered")
        written = tmp_repo / sink_observation.written_path
        if not written.is_file():
            raise ProfileError(f"local inbox sink did not write packet: {written}")
        written_packet = json.loads(written.read_text(encoding="utf-8"))
        if written_packet.get("source_truth") is not False:
            raise ProfileError("written local inbox packet source_truth is not false")

        wake_packet = {
            **packet,
            "sink_refs": ["report-sink:local-inbox", "report-sink:operator-wake-local"],
            "operator_wake_targets": [_minimal_operator_wake_target()],
        }
        wake_observations = report_sinks.deliver_report_packet(
            wake_packet,
            repo_root=tmp_repo,
            overwrite_existing=True,
        )
        if len(wake_observations) != 2:
            raise ProfileError("delivery wake bus did not emit two local observations")
        operator_wake_observations = [
            observation
            for observation in wake_observations
            if observation.sink_ref == "report-sink:operator-wake-local"
        ]
        if len(operator_wake_observations) != 1:
            raise ProfileError("operator wake local sink observation was not emitted")
        wake_written = tmp_repo / operator_wake_observations[0].written_path
        if not wake_written.is_file():
            raise ProfileError(f"operator wake sink did not write packet: {wake_written}")
        wake_written_packet = json.loads(wake_written.read_text(encoding="utf-8"))
        if wake_written_packet.get("source_truth") is not False:
            raise ProfileError("operator wake packet source_truth is not false")
        if not wake_written_packet.get("operator_wake_targets"):
            raise ProfileError("operator wake packet did not preserve wake target refs")

        # CLEAN-YARD v3 (Smith 0611): the 3 standing dogfood inbox packets
        # (run-surface-authority-boundary-0529 / reporter-delivery-wake-bus-0531)
        # left for the frozen museum; their json_required_paths/json_value_paths
        # pin properties are EXECUTED here 1:1 over the packets the REAL sinks
        # just wrote into the temp inbox.
        local_inbox_wake_bus = [
            observation
            for observation in wake_observations
            if observation.sink_ref == "report-sink:local-inbox"
        ]
        if len(local_inbox_wake_bus) != 1:
            raise ProfileError("wake-bus local inbox sink observation was not emitted")
        wake_bus_frontier_packet = json.loads(
            (tmp_repo / local_inbox_wake_bus[0].written_path).read_text(encoding="utf-8")
        )
        _reporter_inbox_packet_shape_fold(
            reporter,
            local_inbox_packet=written_packet,
            wake_bus_frontier_packet=wake_bus_frontier_packet,
            operator_wake_packet=wake_written_packet,
        )

        sink_rejected_complete = False
        try:
            report_sinks.deliver_report_packet(
                {**packet, "complete": True},
                repo_root=tmp_repo,
                overwrite_existing=True,
            )
        except ValueError:
            sink_rejected_complete = True
        if not sink_rejected_complete:
            raise ProfileError("local inbox sink accepted forbidden complete field")

        sink_rejected_raw_secret = False
        try:
            report_sinks.deliver_report_packet(
                {**packet, "raw_secret": "redacted-probe"},
                repo_root=tmp_repo,
                overwrite_existing=True,
            )
        except ValueError:
            sink_rejected_raw_secret = True
        if not sink_rejected_raw_secret:
            raise ProfileError("local inbox sink accepted raw secret shaped field")

        sink_rejected_unadmitted = False
        try:
            report_sinks.deliver_report_packet(
                packet,
                sink_refs=["report-sink:unadmitted"],
                repo_root=tmp_repo,
                overwrite_existing=True,
            )
        except ValueError:
            sink_rejected_unadmitted = True
        if not sink_rejected_unadmitted:
            raise ProfileError("local inbox sink accepted unadmitted sink ref")

    # G6 sink ceiling — re-ratified at FOUR by Smith (0611): report_sinks owns
    # the dispatch seam + exactly these four sinks. The dashboard sink
    # (B-DASH/B-DASH-WIRE) made the set 4 de facto; Smith ratified 4 with the
    # explicit condition that a 5th sink requires the report_bus + sinks/<name>
    # split FIRST (blueprint 3.1) — never a 5th sibling in this module.
    ratified_sink_refs = frozenset(
        {
            "report-sink:local-inbox",
            "report-sink:operator-wake-local",
            "report-sink:slack",
            "report-sink:dashboard",
        }
    )
    admitted_sink_refs = frozenset(report_sinks.ADMITTED_SINK_REFS)
    if admitted_sink_refs != ratified_sink_refs:
        unexpected = sorted(admitted_sink_refs - ratified_sink_refs)
        missing = sorted(ratified_sink_refs - admitted_sink_refs)
        raise ProfileError(
            "G6 sink ceiling violated: ADMITTED_SINK_REFS must be exactly the "
            f"FOUR Smith-ratified (0611) sinks {sorted(ratified_sink_refs)} "
            f"(unexpected={unexpected}, missing={missing}); "
            "a 5th sink requires the report_bus split — never a 5th sibling"
        )

    return KernelResult(
        check_id="reporter_notification_projection",
        inspected=(
            len(observations)
            + len(owner_observations)
            + len(delivery_wake_observations)
            + len(event_hook_observations)
            + label_parity_count
            + agent_incomplete_event_count
            + message_shape_count
            + auto_wire_count
            + brick_grain_count
            + no_scheduler_count
            + 8
        ),
        output=(
            "reporter notification projection passed: "
            f"{len(observations)} reporter negative probe(s), "
            f"{len(owner_observations)} owner vocabulary probe(s), "
            f"{len(delivery_wake_observations)} delivery wake probe(s), "
            f"{len(event_hook_observations)} event hook probe(s), "
            f"{label_parity_count} label parity map(s), "
            f"{agent_incomplete_event_count} agent-incomplete event assertion(s), "
            f"{message_shape_count} Slack message shape assertion(s), "
            f"{auto_wire_count} auto-wire assertion(s), "
            f"{brick_grain_count} brick-grain thread assertion(s), "
            f"{no_scheduler_count} no-scheduler source file(s), "
            "local inbox write, operator wake write, forbidden field rejects, "
            "unadmitted sink reject, and the G6 sink ceiling (4 ratified sinks: "
            "local-inbox, operator-wake-local, slack, dashboard — Smith 0611; "
            "a 5th sink requires the report_bus split, never a 5th sibling) inspected. "
            f"Specimen after renderer: {message_text!r}. "
            f"Temp auto-wire Slack text: {auto_wire_message!r}. "
            f"Verbose-mode temp Slack text: {verbose_mode_text!r}. "
            f"Brick-grain Slack text: {brick_grain_text!r}. "
            f"Disposition Slack text: {disposition_text!r}. "
            f"{dashboard_project_ref_text} "
            f"{structure_diagram_text} "
            f"Temp local inbox packet bytes: {len(auto_wire_inbox_text.encode('utf-8'))}."
        ),
    )
