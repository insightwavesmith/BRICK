"""gemini_local_only_adapter checker-lib leaf.

Support checker mechanics only. This module observes Gemini local adapter
admission/guardrails; it authors no axis crossing and decides no Movement,
success, or quality.
"""

from __future__ import annotations

import importlib
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import KernelResult, ProfileError, _ensure_import_identity


def run_gemini_local_only_adapter(repo: Path) -> KernelResult:
    """Assert the active Gemini customer adapter is gemini-local only."""
    _ensure_import_identity(repo)
    adapter = importlib.import_module("brick_protocol.support.connection.agent_adapter")
    adapter_constants = importlib.import_module("brick_protocol.support.connection.adapter_constants")
    adapter_subprocess = importlib.import_module("brick_protocol.support.connection.adapter_subprocess")
    agent_resources = importlib.import_module("brick_protocol.support.connection.agent_resources")
    gemini_api = adapter_constants.ADAPTER_GEMINI_API
    gemini_local = adapter_constants.ADAPTER_GEMINI_LOCAL
    inspected = 0

    if gemini_local not in adapter_constants.ALLOWED_ADAPTER_REFS:
        raise ProfileError("gemini_local_only_adapter: adapter:gemini-local is not admitted")
    if gemini_api in adapter_constants.ALLOWED_ADAPTER_REFS:
        raise ProfileError("gemini_local_only_adapter: adapter:gemini-api is still admitted")
    if gemini_api in adapter_constants._ADAPTER_CAPABILITIES:
        raise ProfileError("gemini_local_only_adapter: adapter:gemini-api still has capabilities")
    if gemini_api in adapter_constants.MODEL_PROVIDER_BY_ADAPTER:
        raise ProfileError("gemini_local_only_adapter: adapter:gemini-api still has model provider")
    if gemini_api in adapter.local_cli_adapter_refs():
        raise ProfileError("gemini_local_only_adapter: adapter:gemini-api leaked into CLI refs")
    inspected += 1

    # CR.P2 parity pin: gemini-local is in the same Building QA/work Agent
    # capability class as codex-local for repo read + observed workspace write.
    # Extra provider-native projections (review/web) are not authority here; the
    # class proof is the shared read/write capability plus observed-write
    # admission, with gemini-api still retired.
    codex_local = adapter_constants.ADAPTER_CODEX_LOCAL
    required_capability_class = {
        adapter_constants.ADAPTER_CAPABILITY_READ,
        adapter_constants.ADAPTER_CAPABILITY_WRITE,
    }
    codex_capabilities = set(adapter.adapter_capabilities(codex_local))
    gemini_capabilities = set(adapter.adapter_capabilities(gemini_local))
    if not required_capability_class.issubset(codex_capabilities):
        raise ProfileError(
            "gemini_local_only_adapter: codex-local lost the read/write capability class"
        )
    if not required_capability_class.issubset(gemini_capabilities):
        raise ProfileError(
            "gemini_local_only_adapter: gemini-local lost codex-local read/write parity"
        )
    observed_write_refs = set(adapter_constants._OBSERVED_WRITE_ADAPTER_REFS)
    if codex_local not in observed_write_refs or gemini_local not in observed_write_refs:
        raise ProfileError(
            "gemini_local_only_adapter: codex-local and gemini-local must both be "
            "observed-write adapter refs"
        )
    if gemini_api in observed_write_refs:
        raise ProfileError("gemini_local_only_adapter: retired gemini-api is observed-write")
    inspected += 1

    spec = adapter._LOCAL_CLI_SPECS.get(gemini_local)
    if spec is None:
        raise ProfileError("gemini_local_only_adapter: gemini-local missing local CLI spec")
    if spec.executable_name != "gemini":
        raise ProfileError("gemini_local_only_adapter: gemini-local executable must be gemini")
    if spec.invocation_args_kind != "gemini-p-json-flash":
        raise ProfileError("gemini_local_only_adapter: gemini-local invocation kind drifted")
    if spec.default_model_ref != adapter_constants.MODEL_REF_GEMINI_LOCAL_FLASH:
        raise ProfileError("gemini_local_only_adapter: gemini-local default model ref drifted")
    if tuple(adapter._GEMINI_API_KEY_ENV_VARS) != ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        raise ProfileError("gemini_local_only_adapter: Gemini API-key env order drifted")
    from support.checkers.lib.case_runners import _preset_completion_command_runner

    command_runner = _preset_completion_command_runner(adapter.LocalCliCompleted)
    status = adapter_subprocess.preflight_provider(gemini_local, command_runner=command_runner)
    if "api_key_env_present" not in status or status.get("credential_validity") != "not_proven":
        raise ProfileError(
            "gemini_local_only_adapter: gemini-local preflight stopped exposing key presence "
            "with credential_validity=not_proven"
        )
    inspected += 1

    for role in ("inspector", "qa", "qa-lead"):
        packet = agent_resources.resolve_agent_object(f"agent-object:{role}", repo_root=repo)[
            "agent_object"
        ]
        refs = tuple(packet.get("adapter_refs") or ())
        if gemini_api in refs:
            raise ProfileError(
                f"gemini_local_only_adapter: agent-object:{role} still admits adapter:gemini-api"
            )
        if role in {"inspector", "qa-lead"} and gemini_local not in refs:
            raise ProfileError(
                f"gemini_local_only_adapter: agent-object:{role} lost adapter:gemini-local"
            )
        inspected += 1

    try:
        adapter.AgentAdapterRequest(
            building_id="gemini-api-retired-probe",
            agent_object_ref="agent-object:inspector",
            adapter_ref=gemini_api,
            brick_instance_ref="brick-review",
            next_brick_instance_ref="brick-closure",
            work_statement="Return support evidence only.",
        )
    except ValueError as exc:
        if "adapter_ref is not admitted" not in str(exc):
            raise ProfileError(
                "gemini_local_only_adapter: retired gemini-api rejected with wrong reason"
            ) from exc
    else:
        raise ProfileError("gemini_local_only_adapter: retired gemini-api request constructed")
    inspected += 1

    captured: dict[str, Any] = {}

    def _capture_gemini_runner(
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
        captured["args"] = call
        captured["cwd"] = cwd
        captured["env_has_api_key"] = bool(
            (env or {}).get("GEMINI_API_KEY") or (env or {}).get("GOOGLE_API_KEY")
        )
        return adapter.LocalCliCompleted(call, 0, json.dumps({"response": "{}"}), "")

    request = adapter.AgentAdapterRequest(
        building_id="gemini-local-cli-probe",
        agent_object_ref="agent-object:inspector",
        adapter_ref=gemini_local,
        brick_instance_ref="brick-review",
        next_brick_instance_ref="brick-closure",
        tool_policy_refs=(adapter_constants.PROBE_WRITE_TOOL_POLICY_REF,),
        work_statement="Return support evidence only.",
    )
    saved_env = {name: os.environ.get(name) for name in adapter._GEMINI_API_KEY_ENV_VARS}
    for name in adapter._GEMINI_API_KEY_ENV_VARS:
        os.environ.pop(name, None)
    os.environ["GEMINI_API_KEY"] = "probe-key"
    try:
        adapter.connect_agent_brain(
            request,
            command_runner=_capture_gemini_runner,
            cwd=repo,
            timeout_seconds=5,
        )
    finally:
        for name in adapter._GEMINI_API_KEY_ENV_VARS:
            os.environ.pop(name, None)
            if saved_env[name] is not None:
                os.environ[name] = saved_env[name]
    if not captured.get("env_has_api_key"):
        raise ProfileError("gemini_local_only_adapter: gemini-local did not receive API-key env")
    if not captured.get("args") or Path(captured["args"][0]).name != "gemini":
        raise ProfileError("gemini_local_only_adapter: gemini-local did not spawn gemini CLI")
    if captured.get("cwd") != repo:
        raise ProfileError("gemini_local_only_adapter: gemini-local did not run from adapter cwd")
    inspected += 1

    previous_checker_sweep = os.environ.get("BRICK_CHECKER_PROFILE_SWEEP")
    os.environ["BRICK_CHECKER_PROFILE_SWEEP"] = "1"
    saved_env = {name: os.environ.get(name) for name in adapter._GEMINI_API_KEY_ENV_VARS}
    for name in adapter._GEMINI_API_KEY_ENV_VARS:
        os.environ.pop(name, None)
    os.environ["GEMINI_API_KEY"] = "probe-key"
    try:
        try:
            adapter.connect_agent_brain(
                request,
                command_runner=None,
                cwd=repo,
                timeout_seconds=5,
            )
        except ValueError as exc:
            if "checker profile sweep must not invoke live gemini-local CLI" not in str(exc):
                raise ProfileError(
                    "gemini_local_only_adapter: checker-sweep live Gemini guard "
                    "rejected with wrong reason"
                ) from exc
        else:
            raise ProfileError(
                "gemini_local_only_adapter: checker-sweep live Gemini dispatch was not rejected"
            )
    finally:
        if previous_checker_sweep is None:
            os.environ.pop("BRICK_CHECKER_PROFILE_SWEEP", None)
        else:
            os.environ["BRICK_CHECKER_PROFILE_SWEEP"] = previous_checker_sweep
        for name in adapter._GEMINI_API_KEY_ENV_VARS:
            os.environ.pop(name, None)
            if saved_env[name] is not None:
                os.environ[name] = saved_env[name]
    inspected += 1

    return KernelResult(
        check_id="gemini_local_only_adapter",
        inspected=inspected,
        output=(
            "gemini-local-only adapter evidence: adapter:gemini-local is admitted "
            "as Gemini CLI with GEMINI_API_KEY/GOOGLE_API_KEY auth observation; "
            "it shares the codex-local read/write observed-write capability class; "
            "adapter:gemini-api is retired from active admission/capability/model "
            "tables and Agent resource refs; retired requests and checker-sweep "
            "live Gemini dispatch fail closed "
            f"({inspected} group(s) inspected)."
        ),
    )
