#!/usr/bin/env python3
"""Pin the brick-protocol MCP wiring into BOTH local-CLI dispatch branches.

INSTALL-WIZARD-0623 (engine-native A1): a DISPATCHED build CLI must see the
brick-protocol MCP server regardless of the user's own ~/.claude / ~/.codex
config, so the adapter wires it per-invocation:

  - claude branch: ``--mcp-config <inline-json>`` + ``--strict-mcp-config`` (the
    inline JSON names the brick-protocol server; --strict suppresses the user's
    own ~/.claude MCP -- isolation lever #1);
  - codex branch: ``-c mcp_servers.brick-protocol.*`` overrides + ``--ignore-user-config``
    (ignores the user's ~/.codex/config.toml -- isolation lever #2).

This checker is support evidence only. It PARSES (AST, no import) the real
brick_protocol/support/connection/adapter_local_cli.py and asserts that ``_invoke_local_cli``
references BOTH the MCP-config helper for each provider AND the isolation lever
for each provider. It FAILS CLOSED: a branch missing its MCP wire or isolation
lever is RED. It does NOT call providers, run a real CLI, choose Movement, judge
source truth, judge success or quality, or classify Building outcomes.

WHAT THIS DOES NOT PROVE (honesty): the presence of the flag does NOT prove a
dispatched agent actually CALLED a brick MCP tool (a real tools/list round-trip).
That stays NOT-PROVEN until a real adapter:claude-local dispatch observes it --
this checker pins the WIRING shape only, not the provider behavior.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]
_ADAPTER_REL = Path("brick_protocol/support/connection/adapter_local_cli.py")
_INVOKE_FUNC = "_invoke_local_cli"

# The names that MUST appear (as called helpers or literal flag args) inside the
# _invoke_local_cli body for each provider's MCP wire + isolation lever.
_CLAUDE_REQUIRED_NAMES: tuple[str, ...] = ("_claude_mcp_config_json", "--strict-mcp-config")
_CODEX_REQUIRED_NAMES: tuple[str, ...] = ("_codex_mcp_config_cli_args", "--ignore-user-config")

# The single-source helpers that derive the MCP server argv must reuse connect.py
# (one registration shape shared with the connect docs), not a second copy.
_SINGLE_SOURCE_HELPERS: tuple[str, ...] = ("_brick_mcp_server_argv", "_repo_root_for_request")

PROOF_LIMIT = (
    "proof limit: MCP-dispatch-wire checker support evidence only; it pins that the "
    "brick-protocol MCP config + the per-provider isolation lever are wired into both "
    "dispatch branches. It does NOT prove a dispatched agent actually called a brick "
    "MCP tool (a real tools/list round-trip stays NOT-PROVEN until a live dispatch), "
    "nor source truth, success, quality, or Movement authority."
)


class McpDispatchWireError(ValueError):
    """Raised when an MCP dispatch wire or isolation lever is missing from a branch."""


def _parse_adapter(repo: Path) -> ast.Module:
    path = repo / _ADAPTER_REL
    try:
        text = path.read_text(encoding="utf-8")
        return ast.parse(text, filename=str(_ADAPTER_REL))
    except OSError as exc:
        raise McpDispatchWireError(f"could not read {_ADAPTER_REL}: {exc}") from exc
    except SyntaxError as exc:
        raise McpDispatchWireError(f"{_ADAPTER_REL} is not valid Python: {exc}") from exc


def _function_node(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise McpDispatchWireError(f"{_ADAPTER_REL}: missing required function {name}")


def _names_and_strings(func_node: ast.FunctionDef) -> set[str]:
    """Collect every called-name + string literal inside the function body."""

    found: set[str] = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.add(node.value)
    return found


def _module_function_names(module: ast.Module) -> set[str]:
    return {node.name for node in module.body if isinstance(node, ast.FunctionDef)}


def _assert_branch(present: set[str], required: tuple[str, ...], *, branch: str) -> str:
    missing = [name for name in required if name not in present]
    if missing:
        raise McpDispatchWireError(
            f"{_ADAPTER_REL}: {_INVOKE_FUNC} {branch} branch is missing the MCP "
            f"wire / isolation lever name(s): {missing}. A dispatched build CLI "
            "must wire the brick-protocol MCP and ignore the user config."
        )
    return f"{branch}: MCP wire + isolation lever present ({', '.join(required)})"


def check(repo: Path) -> list[str]:
    module = _parse_adapter(repo)
    invoke = _function_node(module, _INVOKE_FUNC)
    present = _names_and_strings(invoke)
    module_funcs = _module_function_names(module)

    lines = [
        _assert_branch(present, _CLAUDE_REQUIRED_NAMES, branch="claude-plan-json"),
        _assert_branch(present, _CODEX_REQUIRED_NAMES, branch="codex-exec-readonly"),
    ]
    missing_helpers = [h for h in _SINGLE_SOURCE_HELPERS if h not in module_funcs]
    if missing_helpers:
        raise McpDispatchWireError(
            f"{_ADAPTER_REL}: missing single-source MCP helper(s): {missing_helpers}. "
            "The dispatch MCP wire must reuse connect.py's registration shape."
        )
    lines.append(
        f"single-source helpers present: {', '.join(_SINGLE_SOURCE_HELPERS)}"
    )
    return [
        "MCP dispatch wire green: brick-protocol MCP + per-provider isolation lever "
        "are wired into both _invoke_local_cli branches.",
        *lines,
        PROOF_LIMIT,
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: the brick-protocol MCP config + the per-provider "
            "isolation lever are wired into both local-CLI dispatch branches."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except McpDispatchWireError as exc:
        print("MCP dispatch wire rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
