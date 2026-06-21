#!/usr/bin/env python3
"""Pin the CLI-runner subprocess spawns to stdin=subprocess.DEVNULL.

CONNECT-STALL PRIMARY CURE (stdin 0619): codex/claude/gemini `exec` unconditionally
read() stdin at startup. When BRICK's process tree inherited an open pipe/FIFO on fd 0
(write-end held open, no data, no EOF), that startup read() blocked FOREVER -- the
"connect-stall" (process alive, ~0 CPU, 0 ESTABLISHED sockets, runs to the adapter
timeout). The two CLI-runner spawns in support/connection/adapter_subprocess.py
(_run_text_cli_command, _run_command; relocated from agent_adapter.py by the
MODULE-SEP god-module split, re-exported by the agent_adapter facade) MUST pass
stdin=subprocess.DEVNULL so the child
gets an immediate stdin EOF and its startup read returns instantly -- structurally
eliminating the stall regardless of how BRICK's parent stdin was wired, regardless of
codex version, regardless of --ephemeral.

This checker is support evidence only. It PARSES (AST, no import) the real
support/connection/adapter_subprocess.py, finds the two named CLI-runner functions, and
asserts the subprocess.Popen call inside each passes a stdin= keyword resolving to
subprocess.DEVNULL. It FAILS CLOSED: a CLI-runner Popen WITHOUT stdin=DEVNULL (or with
a different stdin value) is RED. It does NOT call providers, run a real CLI, choose
Movement, judge source truth, judge success or quality, or classify Building outcomes.

SAFETY OF DEVNULL: BRICK never feeds the CLI via stdin -- the prompt is passed as a
positional/flag argv item (codex `--output-last-message <file> <prompt>`, claude
`... <prompt>`, gemini `-p <prompt>`) and proc.communicate() is called with NO input=
argument. So DEVNULL cannot break any input path. (Verified by grep at fix time; this
checker pins the spawn shape, not the no-stdin-input property.)
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Sequence
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
# MODULE-SEP god-module split: the two CLI-runner functions relocated verbatim
# from agent_adapter.py into the adapter_subprocess.py sibling (re-exported by the
# agent_adapter facade). The pin follows the moved symbols to their new home.
_ADAPTER_REL = Path("support/connection/adapter_subprocess.py")

# The CLI-runner spawns: the ONLY two functions in adapter_subprocess.py that Popen the
# prompt-reading provider CLI (codex/claude/gemini). The ps/lsof helper spawns
# (_process_snapshot_rows, _established_tcp_socket_count) use subprocess.run on
# ps/lsof -- internal probes that never read prompt stdin -- and are out of scope.
CLI_RUNNER_FUNCTIONS = frozenset({"_run_text_cli_command", "_run_command"})

PROOF_LIMIT = (
    "proof limit: CLI-runner stdin-DEVNULL checker support evidence only; it does "
    "not prove source truth, success judgment, quality judgment, Movement authority, "
    "provider behavior, or that the connect-stall never recurs through an unrelated "
    "network hang (the TrackB watchdog remains the defense-in-depth for that)."
)


class CliRunnerStdinDevnullError(ValueError):
    """Raised when a CLI-runner Popen spawn does not pass stdin=subprocess.DEVNULL."""


def _parse_adapter(repo: Path) -> ast.Module:
    path = repo / _ADAPTER_REL
    try:
        text = path.read_text(encoding="utf-8")
        return ast.parse(text, filename=str(_ADAPTER_REL))
    except OSError as exc:
        raise CliRunnerStdinDevnullError(f"could not read {_ADAPTER_REL}: {exc}") from exc
    except SyntaxError as exc:
        raise CliRunnerStdinDevnullError(f"{_ADAPTER_REL} is not valid Python: {exc}") from exc


def _function_node(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            if isinstance(node, ast.AsyncFunctionDef):
                raise CliRunnerStdinDevnullError(
                    f"{_ADAPTER_REL}: CLI runner {name} unexpectedly became async"
                )
            return node
    raise CliRunnerStdinDevnullError(
        f"{_ADAPTER_REL}: missing required CLI-runner function {name}"
    )


def _is_subprocess_popen(call: ast.Call) -> bool:
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "Popen"
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
    )


def _popen_calls(func_node: ast.FunctionDef) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call) and _is_subprocess_popen(node):
            calls.append(node)
    return calls


def _stdin_is_subprocess_devnull(call: ast.Call) -> bool:
    """True iff the Popen call passes stdin=subprocess.DEVNULL (exact node shape)."""
    for keyword in call.keywords:
        if keyword.arg != "stdin":
            continue
        value = keyword.value
        return (
            isinstance(value, ast.Attribute)
            and value.attr == "DEVNULL"
            and isinstance(value.value, ast.Name)
            and value.value.id == "subprocess"
        )
    return False


def _assert_runner_stdin_devnull(module: ast.Module, name: str) -> str:
    func_node = _function_node(module, name)
    popen_calls = _popen_calls(func_node)
    if not popen_calls:
        raise CliRunnerStdinDevnullError(
            f"{_ADAPTER_REL}: CLI runner {name} has no subprocess.Popen spawn "
            "(the CLI-runner shape changed; re-pin this checker deliberately)"
        )
    for index, call in enumerate(popen_calls):
        if not _stdin_is_subprocess_devnull(call):
            raise CliRunnerStdinDevnullError(
                f"{_ADAPTER_REL}: CLI runner {name} subprocess.Popen spawn "
                f"#{index} does not pass stdin=subprocess.DEVNULL -- a child that "
                "inherits an open-no-EOF stdin pipe will block forever at startup "
                "(connect-stall). Add stdin=subprocess.DEVNULL."
            )
    return f"{name}: {len(popen_calls)} subprocess.Popen spawn(s) all pass stdin=subprocess.DEVNULL"


def _assert_mutation_red(module: ast.Module) -> str:
    """A CLI-runner Popen with stdin REMOVED must be rejected (fails closed).

    Builds an in-memory copy of one runner's Popen call with the stdin keyword
    stripped and confirms the same assertion REJECTS it -- so the checker is not
    vacuously green if the real source ever loses its stdin guard.
    """
    name = "_run_command"
    func_node = _function_node(module, name)
    popen_calls = _popen_calls(func_node)
    mutated_call = ast.Call(
        func=popen_calls[0].func,
        args=list(popen_calls[0].args),
        keywords=[kw for kw in popen_calls[0].keywords if kw.arg != "stdin"],
    )
    if _stdin_is_subprocess_devnull(mutated_call):
        raise CliRunnerStdinDevnullError(
            "mutation RED failed: a Popen call with stdin removed was still read as DEVNULL"
        )
    return "mutation RED observed: a CLI-runner Popen with stdin removed is rejected"


def check(repo: Path) -> list[str]:
    module = _parse_adapter(repo)
    runner_lines = [
        _assert_runner_stdin_devnull(module, name)
        for name in sorted(CLI_RUNNER_FUNCTIONS)
    ]
    mutation_line = _assert_mutation_red(module)
    return [
        "CLI-runner stdin=DEVNULL green: "
        f"runners={sorted(CLI_RUNNER_FUNCTIONS)} all spawn with stdin=subprocess.DEVNULL.",
        *runner_lines,
        mutation_line,
        PROOF_LIMIT,
    ]


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Support-evidence checker: the CLI-runner subprocess spawns in "
            "adapter_subprocess.py pass stdin=subprocess.DEVNULL (connect-stall primary cure)."
        )
    )
    parser.add_argument("--repo", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo = Path(args.repo).resolve() if args.repo else _REPO_ROOT
    try:
        outputs = check(repo)
    except CliRunnerStdinDevnullError as exc:
        print("CLI-runner stdin=DEVNULL rejected:", file=sys.stderr)
        print(f"- {exc}", file=sys.stderr)
        print(PROOF_LIMIT, file=sys.stderr)
        return 1
    for line in outputs:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
