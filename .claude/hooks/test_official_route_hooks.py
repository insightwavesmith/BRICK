#!/usr/bin/env python3
"""Unit probes for the Brick official-route Claude hooks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SESSION_HOOK = ROOT / ".claude" / "hooks" / "session_start_official_route.py"
PRETOOL_HOOK = ROOT / ".claude" / "hooks" / "pretooluse_block_offroute_launch.py"
SETTINGS = ROOT / ".claude" / "settings.json"


def _run_hook(script: Path, payload: dict[str, object], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=merged_env,
    )


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _assert_session_start() -> None:
    for source in ("startup", "resume", "clear", "compact"):
        result = _run_hook(SESSION_HOOK, {"source": source})
        _assert(result.returncode == 0, f"SessionStart {source} exited {result.returncode}")
        body = json.loads(result.stdout)
        output = body["hookSpecificOutput"]
        context = output["additionalContext"]
        _assert(output["hookEventName"] == "SessionStart", f"bad event for {source}")
        _assert("brick build" in context and "brick resume" in context, f"missing verbs for {source}")
        _assert("python -m brick_protocol.support.operator.cli" in context, f"missing module CLI for {source}")
        _assert("_run_dynamic_graph_walker" in context, f"missing bypass list for {source}")


def _assert_denied(command: str, env: dict[str, str] | None = None) -> None:
    result = _run_hook(PRETOOL_HOOK, {"command": command}, env=env)
    _assert(result.returncode == 0, f"deny case exited {result.returncode}: {command}")
    body = json.loads(result.stdout)
    output = body["hookSpecificOutput"]
    _assert(output["hookEventName"] == "PreToolUse", f"bad event: {command}")
    _assert(output["permissionDecision"] == "deny", f"not denied: {command}")


def _assert_allowed(command: str, env: dict[str, str] | None = None) -> None:
    result = _run_hook(PRETOOL_HOOK, {"command": command}, env=env)
    _assert(result.returncode == 0, f"allow case exited {result.returncode}: {command}")
    _assert(result.stdout == "", f"allow case produced output: {command} -> {result.stdout!r}")


def _assert_pretooluse() -> None:
    deny_cases = (
        "python -c 'from brick_protocol.support.operator.walker_kernel import _run_dynamic_graph_walker'",
        "python -c 'from brick_protocol.support.operator.dynamic_walker import _resume_dynamic_graph_walker'",
        "python -c 'from brick_protocol.support.operator.run import run_building_plan'",
        "python -c 'from brick_protocol.support.operator.run import run_building_once'",
        "python -c 'from brick_protocol.support.operator.run import resume_building_plan'",
        "python -c 'from brick_protocol.support.operator.onboard import launch_assembled_building'",
        "python -m brick_protocol.support.operator.onboard",
        "python3 -m brick_protocol.support.operator.onboard --goal-approve /tmp/building",
        "python -c 'from brick_protocol.support.operator.driver import run_customer_graph_building_in_sandbox'",
        "python /tmp/launch_building.py",
        "python -c 'import os; os.system(\"run_building_plan\")'",
        "brick build && python -c 'from brick_protocol.support.operator.run import run_building_plan'",
        "brick build\npython -c 'from brick_protocol.support.operator.run import run_building_plan'",
        "brick build | python -c 'print(123)'",
    )
    for command in deny_cases:
        _assert_denied(command)
    nested_payload = {
        "tool_input": {
            "command": "python -c 'from brick_protocol.support.operator.run import run_building_plan'"
        }
    }
    result = _run_hook(PRETOOL_HOOK, nested_payload)
    _assert(result.returncode == 0, "nested command payload exited nonzero")
    _assert(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny", "nested command payload was not denied")

    allow_cases = (
        "brick build",
        "brick resume --from latest",
        "python -m brick_protocol.support.operator.cli build",
        "python -m brick_protocol.support.operator.cli resume --building x",
        "brick build > log.txt 2>&1",
        "python -m brick_protocol.support.operator.cli resume 2>&1 | tee log.txt",
        "python -c 'print(123)'",
        "ls -la",
    )
    for command in allow_cases:
        _assert_allowed(command)


def _assert_mutation_probes() -> None:
    _assert_denied(
        "brick build",
        env={"BRICK_HOOK_TEST_DISABLE_OFFICIAL_ALLOW": "1"},
    )
    _assert_allowed(
        "python -c 'from brick_protocol.support.operator.walker_kernel import _run_dynamic_graph_walker'",
        env={"BRICK_HOOK_TEST_REMOVE_DENY_PATTERN": "_run_dynamic_graph_walker"},
    )
    _assert_allowed(
        "python -m brick_protocol.support.operator.onboard",
        env={"BRICK_HOOK_TEST_REMOVE_DENY_PATTERN": "operator\\.onboard"},
    )


def _assert_fail_open() -> None:
    for script in (SESSION_HOOK, PRETOOL_HOOK):
        result = _run_hook(script, {"source": "startup", "command": "run_building_plan"}, env={"BRICK_HOOK_FORCE_ERROR": "1"})
        _assert(result.returncode == 0, f"forced error did not fail open: {script}")
        _assert(result.stdout == "", f"forced error produced output: {script}")


def main() -> int:
    json.loads(SETTINGS.read_text(encoding="utf-8"))
    _assert_session_start()
    _assert_pretooluse()
    _assert_mutation_probes()
    _assert_fail_open()
    print("official-route hook probes passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
