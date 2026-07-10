#!/usr/bin/env python3
"""Claude PreToolUse Bash hook: deny non-official Brick launch commands."""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from dataclasses import dataclass
from typing import Iterable


DENY_REASON = (
    "Off-route Building launch. Use `brick build`/`brick resume` "
    "(or `python -m brick_protocol.support.operator.cli build|resume`). "
    "Direct walker/run/onboard/driver imports are non-official and are blocked."
)

DEFAULT_DENY_PATTERNS = (
    r"\b_run_dynamic_graph_walker\b",
    r"\b_resume_dynamic_graph_walker\b",
    r"\brun_building_plan\b",
    r"\brun_building_once\b",
    r"\bresume_building_plan\b",
    r"\blaunch_assembled_building\b",
    r"\brun_customer_graph_building_in_sandbox\b",
    r"\bpython(?:3(?:\.\d+)?)?\s+-m\s+brick_protocol\.support\.operator\.onboard\b",
)

WRAPPER_PATTERNS = (
    r"\bsubprocess\.(?:run|call|Popen|check_call|check_output)\b",
    r"\bos\.system\b",
)

OFFICIAL_BRICK_RE = re.compile(r"^\s*brick\s+(?:build|resume)(?:\s|$)")
OFFICIAL_MODULE_RE = re.compile(
    r"^\s*python(?:3(?:\.\d+)?)?\s+-m\s+brick_protocol\.support\.operator\.cli\s+"
    r"(?:build|resume)(?:\s|$)"
)
PYTHON_FILE_RE = re.compile(r"^\s*python(?:3(?:\.\d+)?)?\s+(?!-m\b)(?:\S+/)?\S+\.py(?:\s|$)")
SHELL_CHAIN_RE = re.compile(r"&&|;|\|\||`|\$\(|[\r\n]")


@dataclass(frozen=True)
class Decision:
    deny: bool
    reason: str = ""


def _load_command() -> str:
    raw = sys.stdin.read()
    if not raw.strip():
        return ""
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        return ""
    command = loaded.get("command", "")
    if isinstance(command, str) and command:
        return command
    tool_input = loaded.get("tool_input", {})
    if isinstance(tool_input, dict):
        nested_command = tool_input.get("command", "")
        if isinstance(nested_command, str):
            return nested_command
    return ""


def _configured_deny_patterns() -> tuple[str, ...]:
    patterns = list(DEFAULT_DENY_PATTERNS)
    remove = os.environ.get("BRICK_HOOK_TEST_REMOVE_DENY_PATTERN", "")
    if remove:
        patterns = [pattern for pattern in patterns if remove not in pattern]
    return tuple(patterns)


def _official_allow_enabled() -> bool:
    return os.environ.get("BRICK_HOOK_TEST_DISABLE_OFFICIAL_ALLOW") != "1"


def _strip_redirect_tokens(segment: str) -> str:
    tokens = shlex.split(segment, posix=True)
    kept: list[str] = []
    skip_next = False
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        if re.fullmatch(r"\d?>&\d", token):
            continue
        if re.fullmatch(r"\d?>{1,2}", token):
            skip_next = True
            continue
        if re.fullmatch(r"\d?>{1,2}\S+", token):
            continue
        kept.append(token)
    return " ".join(kept)


def _is_tee_segment(segment: str) -> bool:
    try:
        tokens = shlex.split(segment, posix=True)
    except ValueError:
        return False
    return bool(tokens) and tokens[0] == "tee"


def _is_official_command(command: str) -> bool:
    if not _official_allow_enabled():
        return False
    if SHELL_CHAIN_RE.search(command):
        return False
    try:
        pipe_segments = [part.strip() for part in command.split("|")]
        first = _strip_redirect_tokens(pipe_segments[0])
    except ValueError:
        return False
    if not (OFFICIAL_BRICK_RE.match(first) or OFFICIAL_MODULE_RE.match(first)):
        return False
    return all(_is_tee_segment(segment) for segment in pipe_segments[1:])


def _looks_like_official_command(command: str) -> bool:
    try:
        first = _strip_redirect_tokens(command.split("|")[0].strip())
    except ValueError:
        return False
    return bool(OFFICIAL_BRICK_RE.match(first) or OFFICIAL_MODULE_RE.match(first))


def _matches_any(command: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, command) for pattern in patterns)


def classify_command(command: str) -> Decision:
    if not command.strip():
        return Decision(False)

    if _is_official_command(command):
        return Decision(False)

    if _looks_like_official_command(command):
        return Decision(True, DENY_REASON)

    deny_patterns = _configured_deny_patterns()
    if _matches_any(command, deny_patterns):
        return Decision(True, DENY_REASON)

    if _matches_any(command, WRAPPER_PATTERNS) and _matches_any(command, deny_patterns):
        return Decision(True, DENY_REASON)

    if PYTHON_FILE_RE.match(command) and "brick_protocol.support.operator.cli" not in command:
        return Decision(True, DENY_REASON)

    return Decision(False)


def _deny_output(reason: str) -> dict[str, object]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def main() -> int:
    try:
        if os.environ.get("BRICK_HOOK_FORCE_ERROR") == "1":
            raise RuntimeError("forced hook error")
        decision = classify_command(_load_command())
        if decision.deny:
            print(json.dumps(_deny_output(decision.reason), ensure_ascii=False))
    except Exception:
        # Fail open: a hook bug must not block ordinary Bash use.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
